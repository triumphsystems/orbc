import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from core.adapters.base import DocumentGenerator, DocumentParser, DocumentRedactor
from core.adapters.documents.factory import DocumentAdapterFactory
from core.adapters.storage.cloud_storage import CloudStorageSink
from core.adapters.storage.database_sink import DatabaseExportSink
from core.adapters.storage.local_export import LocalFileExportSink
from core.adapters.storage.s3_export import S3ExportSink
from core.agent.brain import AgentBrain
from core.agent.condition import ConditionEvaluator
from core.config.settings import get_settings
from core.db.orm import Automation, Result, Run
from core.utils.sanitizer import sanitize_error_message
from core.events.bus import event_bus
from core.events.types import OrbitEvent
from core.models.enums import Frequency, RunStatus
from core.models.execution_plan import ExecutionPlan
from core.notifications.service import NotificationService
from core.pipeline.discovery.composite import CompositeDiscovery
from core.pipeline.extraction.llm_extractor import LLMExtractor
from core.pipeline.retrieval.link_extractor import LinkExtractor
from core.pipeline.retrieval.proxy import ProxyRetrieval
from core.pipeline.validation.anomaly_detector import AnomalyDetector
from core.pipeline.validation.schema_validator import SchemaValidator
from core.pipeline.verification.engine import VerificationEngine
from core.scheduler.cron import calculate_next_run

logger = logging.getLogger("core.agent.orchestrator")


class RunPoolManager:
    """Manages the global bounded concurrency pool for active mission executions (Layer 3 Protection)."""

    _semaphore: ClassVar[asyncio.Semaphore | None] = None
    _active_run_ids: ClassVar[set[str]] = set()

    @classmethod
    def get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            settings = get_settings()
            cls._semaphore = asyncio.Semaphore(settings.max_concurrent_runs)
        return cls._semaphore

    @classmethod
    def set_limit(cls, limit: int) -> None:
        """Dynamically reconfigures the concurrency limit (useful for testing or runtime tuning)."""
        cls._semaphore = asyncio.Semaphore(limit)

    @classmethod
    def get_active_count(cls) -> int:
        return len(cls._active_run_ids)

    @classmethod
    def is_run_active(cls, run_id: str) -> bool:
        return run_id in cls._active_run_ids

    @classmethod
    def mark_active(cls, run_id: str) -> None:
        cls._active_run_ids.add(run_id)

    @classmethod
    def mark_inactive(cls, run_id: str) -> None:
        cls._active_run_ids.discard(run_id)


class AgentOrchestrator:
    """The central agentic execution engine that executes goal-driven web data operations with checkpointing & self-healing."""

    discovery: CompositeDiscovery
    retrieval: ProxyRetrieval
    extractor: LLMExtractor
    validator: SchemaValidator
    evaluator: ConditionEvaluator
    notifier: NotificationService
    brain: AgentBrain
    link_extractor: LinkExtractor
    anomaly_detector: AnomalyDetector
    verification: VerificationEngine
    export_sink: LocalFileExportSink
    doc_parser: DocumentParser
    doc_generator: DocumentGenerator
    doc_redactor: DocumentRedactor
    cloud_storage: CloudStorageSink
    s3_sink: S3ExportSink
    db_sink: DatabaseExportSink

    def __init__(
        self,
        discovery: CompositeDiscovery | None = None,
        retrieval: ProxyRetrieval | None = None,
        extractor: LLMExtractor | None = None,
        validator: SchemaValidator | None = None,
        evaluator: ConditionEvaluator | None = None,
        notifier: NotificationService | None = None,
        brain: AgentBrain | None = None,
        link_extractor: LinkExtractor | None = None,
        anomaly_detector: AnomalyDetector | None = None,
        verification: VerificationEngine | None = None,
        export_sink: LocalFileExportSink | None = None,
        doc_parser: DocumentParser | None = None,
        doc_generator: DocumentGenerator | None = None,
        doc_redactor: DocumentRedactor | None = None,
        cloud_storage: CloudStorageSink | None = None,
        s3_sink: S3ExportSink | None = None,
        db_sink: DatabaseExportSink | None = None,
    ):
        self.discovery = discovery or CompositeDiscovery()
        self.retrieval = retrieval or ProxyRetrieval()
        self.extractor = extractor or LLMExtractor()
        self.validator = validator or SchemaValidator()
        self.evaluator = evaluator or ConditionEvaluator()
        self.notifier = notifier or NotificationService()
        self.brain = brain or AgentBrain()
        self.link_extractor = link_extractor or LinkExtractor()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.verification = verification or VerificationEngine()
        self.export_sink = export_sink or LocalFileExportSink()
        self.doc_parser = doc_parser or DocumentAdapterFactory.get_parser()
        self.doc_generator = doc_generator or DocumentAdapterFactory.get_generator()
        self.doc_redactor = doc_redactor or DocumentAdapterFactory.get_redactor()
        self.cloud_storage = cloud_storage or CloudStorageSink()
        self.s3_sink = s3_sink or S3ExportSink()
        self.db_sink = db_sink or DatabaseExportSink()

    def _safe_commit(self, db: Session) -> None:
        """Commits changes with defensive rollback and logging on database errors."""
        try:
            db.commit()
        except (OperationalError, DBAPIError) as e:
            logger.error("Database operational error encountered during commit: %s. Rolling back.", e)
            try:
                db.rollback()
            except Exception:
                pass
            raise

    async def execute_run(
        self,
        db: Session,
        automation: Automation,
        run: Run | None = None,
        resume: bool = False,
    ) -> Run:
        try:
            plan = ExecutionPlan.model_validate(automation.plan)
        except Exception as e:
            logger.warning(
                "Failed to validate execution plan for automation %s (%s). Falling back to basic plan.",
                automation.id,
                e,
            )
            plan = ExecutionPlan(
                objective=automation.raw_goal or "Execution Plan",
                search_query=automation.raw_goal or "",
            )

        if run is None:
            run = Run(
                automation_id=automation.id,
                status=RunStatus.discovering,
                reasoning_log=[],
            )
            db.add(run)
            self._safe_commit(db)
            db.refresh(run)
        else:
            # If resuming an existing run, reset error and finish timestamps
            run.error = None
            run.finished_at = None
            self._safe_commit(db)

        await event_bus.publish(
            OrbitEvent(
                event_type="run.started" if not resume else "run.resumed",
                run_id=run.id,
                automation_id=automation.id,
                message=f"{'Resuming' if resume else 'Starting'} autonomous run for goal: {automation.raw_goal}",
            )
        )

        # Layer 3: Global Concurrency Pool (Wait and queue if capacity reached)
        sem = RunPoolManager.get_semaphore()
        if sem.locked():
            run.status = RunStatus.pending
            self._safe_commit(db)
            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message="Mission queued in concurrency pool (waiting for execution slot)",
                    payload={"stage": "pending"},
                )
            )

        async with sem:
            RunPoolManager.mark_active(run.id)
            try:
                return await self._execute_run_internal(db, automation, run, plan, resume)
            finally:
                RunPoolManager.mark_inactive(run.id)

    async def _execute_run_internal(
        self,
        db: Session,
        automation: Automation,
        run: Run,
        plan: ExecutionPlan,
        resume: bool = False,
    ) -> Run:
        reasoning_trail: list[dict[str, Any]] = list(run.reasoning_log or [])

        try:
            # ────────────────────────────────────────────────
            # 1. DISCOVERY STAGE (Checkpoint + Autonomous Retries)
            # ────────────────────────────────────────────────
            urls: list[str] = list(run.sources_found or [])
            if not urls:
                run.status = RunStatus.discovering
                self._safe_commit(db)
                await event_bus.publish(
                    OrbitEvent(
                        event_type="run.stage",
                        run_id=run.id,
                        automation_id=automation.id,
                        message=f"Discovery started for query: {plan.search_query}",
                        payload={"stage": "discovering"},
                    )
                )

                current_query = plan.search_query
                max_discovery_retries = 3
                for attempt in range(1, max_discovery_retries + 1):
                    search_plan = plan.model_copy(update={"search_query": current_query})
                    urls = await self.discovery.discover(search_plan, max_results=8)
                    if urls:
                        break

                    logger.info(f"Discovery attempt {attempt}/{max_discovery_retries} yielded 0 sources. Consulting Agent Brain...")
                    diagnosis = await self.brain.diagnose_and_recover(
                        stage="discovery",
                        error=f"No search results returned for query '{current_query}' (attempt {attempt})",
                        plan=plan,
                    )
                    reasoning_trail.append({"stage": "discovery", "attempt": attempt, "decision": diagnosis})
                    run.reasoning_log = reasoning_trail
                    self._safe_commit(db)

                    if diagnosis.get("can_recover") and diagnosis.get("new_search_query"):
                        current_query = diagnosis["new_search_query"]

                    if attempt < max_discovery_retries:
                        await asyncio.sleep(2 * attempt)

                run.sources_found = urls
                run.reasoning_log = reasoning_trail
                self._safe_commit(db)

                if not urls:
                    run.status = RunStatus.failed
                    run.error = "Discovery failed: no relevant web sources could be identified after multiple self-healing attempts."
                    run.finished_at = datetime.now(timezone.utc)
                    if automation.active and plan.frequency != Frequency.once and not automation.next_run_at:
                        next_run = calculate_next_run(
                            frequency=plan.frequency,
                            schedule_time=plan.schedule_time,
                            tz_name=plan.timezone,
                        )
                        if next_run:
                            automation.next_run_at = next_run
                    self._safe_commit(db)
                    await event_bus.publish(
                        OrbitEvent(
                            event_type="run.failed",
                            run_id=run.id,
                            automation_id=automation.id,
                            message=run.error,
                            payload={"stage": "discovering", "error": run.error},
                        )
                    )
                    return run
            else:
                logger.info(f"Resuming run {run.id}: reusing {len(urls)} checkpointed discovery source(s).")
                reasoning_trail.append({
                    "stage": "discovery",
                    "step": "checkpoint_reused",
                    "message": f"Reused {len(urls)} checkpointed source URLs from previous execution state.",
                })
                run.reasoning_log = reasoning_trail
                self._safe_commit(db)

            # ────────────────────────────────────────────────
            # 2. RETRIEVAL STAGE (Resilient Proxy, Checkpointing & 2-Hop Detail Links)
            # ────────────────────────────────────────────────
            run.status = RunStatus.retrieving
            self._safe_commit(db)
            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message=f"Retrieval started for {len(urls)} source URL(s)",
                    payload={"stage": "retrieving", "sources": urls},
                )
            )

            pages: dict[str, str | None] = {}
            max_retrieval_retries = 3
            target_urls = list(urls)

            for attempt in range(1, max_retrieval_retries + 1):
                missing_urls = [u for u in target_urls if not pages.get(u)]
                if not missing_urls:
                    break

                new_pages = await self.retrieval.retrieve_many(
                    missing_urls, country_code=plan.country_code, concurrency=4
                )
                pages.update(new_pages)

                successful = [u for u, p in pages.items() if p]
                if successful or attempt == max_retrieval_retries:
                    break

                logger.warning(f"Retrieval attempt {attempt}/{max_retrieval_retries} retrieved 0 pages. Pausing before self-healing retry...")
                diagnosis = await self.brain.diagnose_and_recover(
                    stage="retrieval",
                    error="All target web sources failed to load or were blocked by target hosts",
                    plan=plan,
                    sources=target_urls,
                )
                reasoning_trail.append({"stage": "retrieval", "attempt": attempt, "decision": diagnosis})
                run.reasoning_log = reasoning_trail
                self._safe_commit(db)
                await asyncio.sleep(3 * attempt)

            # Self-correction / Autonomous 2-hop navigation
            target_detail_urls: list[str] = []
            for url, content in pages.items():
                if content:
                    child_links = self.link_extractor.extract_child_links(url, content, max_links=3)
                    if child_links:
                        logger.info(f"2-hop navigation: found {len(child_links)} child detail URL(s) from {url}")
                        target_detail_urls.extend(child_links)
                    else:
                        target_detail_urls.append(url)
                else:
                    target_detail_urls.append(url)

            # Deduplicate target detail URLs
            seen_targets = set()
            deduped_targets = []
            for t in target_detail_urls:
                if t not in seen_targets:
                    seen_targets.add(t)
                    deduped_targets.append(t)

            if len(deduped_targets) > len(urls):
                logger.info(f"Retrieving {len(deduped_targets)} detail pages following 2-hop expansion...")
                new_detail_pages = await self.retrieval.retrieve_many(
                    [u for u in deduped_targets if u not in pages or not pages.get(u)],
                    country_code=plan.country_code,
                    concurrency=4,
                )
                pages.update(new_detail_pages)

            run.pages_retrieved = [u for u, p in pages.items() if p]
            self._safe_commit(db)

            # ────────────────────────────────────────────────
            # 3. EXTRACTION STAGE (Schema-Driven & Concurrent)
            # ────────────────────────────────────────────────
            run.status = RunStatus.extracting
            self._safe_commit(db)
            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message=f"Extraction started across {len(pages)} retrieved page(s)",
                    payload={"stage": "extracting"},
                )
            )

            extracted_records: list[dict[str, Any]] = []
            valid_pages = [(u, c) for u, c in pages.items() if c]

            if valid_pages:
                extract_sem = asyncio.Semaphore(4)

                async def _extract_page(u: str, c: str) -> dict[str, Any]:
                    async with extract_sem:
                        return await self.extractor.extract(u, c, plan)

                extracted_records = list(await asyncio.gather(*(_extract_page(u, c) for u, c in valid_pages)))

            # If 0 records were successfully extracted, invoke brain once for diagnostic recovery
            successful_records = [r for r in extracted_records if r.get("extracted", True)]
            if not successful_records and valid_pages:
                diagnosis = await self.brain.diagnose_and_recover(
                    stage="extraction",
                    error="All retrieved pages yielded empty extraction payloads against target schema",
                    plan=plan,
                    sources=[u for u, _ in valid_pages],
                )
                reasoning_trail.append({"stage": "extraction", "decision": diagnosis})

            run.extracted_count = len(extracted_records)
            self._safe_commit(db)

            # ────────────────────────────────────────────────
            # 4. VALIDATION & ANOMALY DETECTION
            # ────────────────────────────────────────────────
            run.status = RunStatus.validating
            self._safe_commit(db)
            await event_bus.publish(
                OrbitEvent(
                    event_type="run.stage",
                    run_id=run.id,
                    automation_id=automation.id,
                    message="Validation and anomaly detection started",
                    payload={"stage": "validating"},
                )
            )

            # Statistical anomaly check across all numeric fields in plan schema
            annotated_records = self.anomaly_detector.filter_and_annotate_outliers(
                extracted_records, plan=plan
            )

            valid_count = 0
            valid_records = []

            # If resuming, clear old results for this run before saving refreshed results
            db.query(Result).filter(Result.run_id == run.id).delete()

            for rec in annotated_records:
                is_valid, errors = self.validator.validate(rec, plan)
                if is_valid:
                    valid_count += 1
                    valid_records.append(rec)

                result_row = Result(
                    run_id=run.id,
                    url=rec.get("url"),
                    data=rec.get("data") if isinstance(rec.get("data"), dict) else {},
                    valid=is_valid,
                    validation_errors=errors if errors else None,
                )
                db.add(result_row)

            run.validated_count = valid_count
            run.status = RunStatus.storing
            self._safe_commit(db)

            await event_bus.publish(
                OrbitEvent(
                    event_type="run.records",
                    run_id=run.id,
                    automation_id=automation.id,
                    message=f"Validated and stored {valid_count} verified record(s)",
                    payload={"validated_count": valid_count, "total_extracted": len(annotated_records)},
                )
            )

            # ────────────────────────────────────────────────
            # 4. STORAGE & EXPORT STAGE (Trigger Configured Adapters Only)
            # ────────────────────────────────────────────────
            has_persisted = True
            dossier_url: str | None = None
            if valid_records:
                try:
                    # 1. Check if Document Dossier Generator is configured in workflow nodes
                    dossier_node = None
                    if plan.workflow_nodes:
                        for node in plan.workflow_nodes:
                            if node.get("typeId") in ("pdf_report", "dossier", "template_report") or node.get("category") == "dossier":
                                dossier_node = node
                                break

                    dossier_bytes: bytes | None = None
                    if dossier_node:
                        node_config = dossier_node.get("config", {})
                        style = node_config.get("style") or ("template" if "template" in dossier_node.get("typeId", "") else "html")
                        template_id = node_config.get("template_id") or node_config.get("template_guid")
                        doc_gen = DocumentAdapterFactory.get_generator(style=style)

                        raw_dossier = await doc_gen.generate_dossier(
                            automation.id,
                            run.id,
                            valid_records,
                            plan_summary=plan.objective,
                            template_id=template_id,
                            sources=run.sources_found or run.pages_retrieved or [],
                        )
                        dossier_bytes = await self.doc_redactor.redact_pii(raw_dossier)

                    # 2. Local File Export (Always active for local audit trail)
                    await self.export_sink.export_results(
                        automation.id, run.id, valid_records, dossier_bytes=dossier_bytes, dossier_filename="dossier.pdf"
                    )

                    # 3. Platform Cloud Storage (Managed GCS / S3 for internal mission artifacts & UI downloads)
                    await self.cloud_storage.export_results(
                        automation.id, run.id, valid_records, dossier_bytes=dossier_bytes, dossier_filename="dossier.pdf"
                    )

                    # 4. User Destination S3 Sink — Trigger only if custom S3 node is in workflow DAG
                    s3_node = None
                    if plan.workflow_nodes:
                        for node in plan.workflow_nodes:
                            if node.get("typeId") in ("s3_storage", "s3", "7") or (node.get("category") == "storage" and "s3" in node.get("label", "").lower()):
                                s3_node = node
                                break

                    if s3_node:
                        cfg = s3_node.get("config", {})
                        if cfg.get("access_key") and cfg.get("secret_key"):
                            custom_s3 = S3ExportSink(
                                bucket_name=cfg.get("bucket_name") or "orbit-exports",
                                endpoint_url=cfg.get("endpoint_url") or None,
                                access_key=cfg.get("access_key"),
                                secret_key=cfg.get("secret_key"),
                                region=cfg.get("region") or "us-east-1",
                            )
                            await custom_s3.export_results(
                                automation.id, run.id, valid_records, dossier_bytes=dossier_bytes, dossier_filename="dossier.pdf"
                            )
                            dossier_url = custom_s3.generate_presigned_url(automation.id, run.id, "dossier.pdf")

                    # 5. Database Persistence Sink — Trigger only if database node is configured
                    has_db_node = any(
                        node.get("typeId") in ("sql_database", "database", "postgres", "8")
                        or (node.get("category") == "storage" and "sql" in node.get("typeId", ""))
                        for node in (plan.workflow_nodes or [])
                    )
                    if has_db_node:
                        await self.db_sink.export_results(
                            automation.id, run.id, valid_records
                        )

                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Export sink notification error: {e}")
                    has_persisted = False

            # ────────────────────────────────────────────────
            # 5. CONDITION EVALUATION & HISTORICAL COMPARISON
            # ────────────────────────────────────────────────
            if plan.condition and valid_records:
                run.status = RunStatus.evaluating
                self._safe_commit(db)

                # Fetch previous run records for historical delta calculations
                previous_records = self._get_previous_run_records(db, automation.id, run.id)

                matched, cond_msg = self.evaluator.evaluate(
                    plan.condition, valid_records, previous_records=previous_records
                )
                run.condition_matched = matched
                run.condition_message = cond_msg
                self._safe_commit(db)

                if matched:
                    run.status = RunStatus.alerting
                    self._safe_commit(db)

                    # Extract target recipient email if configured on workflow nodes
                    recipient_email = None
                    if plan.workflow_nodes:
                        for node in plan.workflow_nodes:
                            if node.get("typeId") in ("email_alert", "email") or node.get("category") == "notify":
                                recipient_email = node.get("config", {}).get("recipient_email")
                                if recipient_email:
                                    break

                    await self.notifier.notify(
                        title=f"Orbit Alert: {plan.objective}",
                        message=cond_msg,
                        payload={"automation_id": automation.id, "run_id": run.id, "dossier_url": dossier_url},
                        channel=plan.notification_channel,
                        recipient_email=recipient_email,
                        dossier_url=dossier_url,
                    )

            # ────────────────────────────────────────────────
            # 6. TIMEZONE-AWARE WALL-CLOCK SCHEDULING
            # ────────────────────────────────────────────────
            next_run = None
            if automation.active and plan.frequency != Frequency.once:
                next_run = calculate_next_run(
                    frequency=plan.frequency,
                    schedule_time=plan.schedule_time,
                    tz_name=plan.timezone,
                )
                if next_run:
                    automation.next_run_at = next_run
                    self._safe_commit(db)

            # ────────────────────────────────────────────────
            # 7. VERIFICATION STAGE
            # ────────────────────────────────────────────────
            verification_report = self.verification.verify_run(
                plan=plan,
                sources=urls,
                pages=pages,
                extracted_records=extracted_records,
                validated_records=valid_records,
                results_persisted=has_persisted,
                next_run_at=automation.next_run_at,
            )

            reasoning_trail.append({"stage": "verification", "report": verification_report.to_dict()})
            run.reasoning_log = reasoning_trail

            if verification_report.verified:
                run.status = RunStatus.verified
            else:
                run.status = RunStatus.failed
                run.error = f"Verification failed: {verification_report.summary}"

            run.finished_at = datetime.now(timezone.utc)
            self._safe_commit(db)

            await event_bus.publish(
                OrbitEvent(
                    event_type="run.completed",
                    run_id=run.id,
                    automation_id=automation.id,
                    message=f"Run finished with status {run.status.value}",
                    payload={"valid_count": valid_count, "extracted_count": len(extracted_records)},
                )
            )

            return run

        except Exception as e:
            logger.exception("Unexpected error in orchestrator")
            try:
                db.rollback()
                run.status = RunStatus.failed
                run.error = sanitize_error_message(str(e))
                run.finished_at = datetime.now(timezone.utc)
                db.add(run)

                # Ensure recurring automations are not permanently descheduled on unexpected failure
                if automation.active and plan.frequency != Frequency.once and not automation.next_run_at:
                    next_run = calculate_next_run(
                        frequency=plan.frequency,
                        schedule_time=plan.schedule_time,
                        tz_name=plan.timezone,
                    )
                    if next_run:
                        automation.next_run_at = next_run
                        db.add(automation)

                db.commit()
            except Exception as persist_err:
                logger.exception(f"Failed to persist run failure state: {persist_err}")
                try:
                    db.rollback()
                except Exception:
                    pass
            return run

    def _get_previous_run_records(
        self, db: Session, automation_id: str, current_run_id: str
    ) -> list[dict[str, Any]]:
        """Retrieves valid records from the most recent previous run of this automation."""
        last_run = (
            db.query(Run)
            .filter(
                Run.automation_id == automation_id,
                Run.id != current_run_id,
                Run.validated_count > 0,
            )
            .order_by(Run.started_at.desc())
            .first()
        )
        if not last_run:
            return []

        return [
            {"url": r.url, "data": r.data, "valid": r.valid}
            for r in last_run.results
            if r.valid
        ]
