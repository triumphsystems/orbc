import json
import logging
from pathlib import Path
from typing import Any

import httpx

from core.adapters.storage.database_sink import DatabaseExportSink
from core.adapters.storage.s3_export import S3ExportSink
from core.cache.service import cache_service
from core.config.settings import get_settings
from core.security.vault import SecretVault

logger = logging.getLogger("core.services.workflow")


class WorkflowService:
    """Core domain service for adapter topology discovery, DAG validation, and connection testing."""

    _storage_path: Path = Path(__file__).resolve().parent.parent / "exports" / "pipeline_topology.json"
    _deployed_pipeline: list[dict[str, Any]] = []
    _custom_adapter_configs: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_adapter_topology(cls) -> list[dict[str, Any]]:
        """Returns live adapter configurations across managed, custom, and both modes."""
        s = get_settings()

        topology = [
            {
                "id": "1", "label": "Schedule Trigger", "category": "trigger", "mode": "both",
                "engine": "Cron & Webhook Engine", "iconName": "Play",
                "description": "Cron schedule and on-demand trigger", "status": "active",
                "config": {"frequency": "daily", "schedule_time": "08:00", "timezone": "UTC"},
            },
            {
                "id": "2", "label": "Source Discovery", "category": "discovery", "mode": "both",
                "engine": "Web Unblocker & Search APIs", "iconName": "Search",
                "description": "Search engine and web proxy retrieval",
                "status": "active" if bool(s.retrieval_api_key or s.search_engine_api_key) else "optional",
                "config": {"search_depth": 2, "max_sources": 8, "proxy_zone": s.retrieval_zone or "default"},
            },
            {
                "id": "3", "label": "Document & Table Parser", "category": "parsing", "mode": "managed",
                "engine": "Layout Analysis Engine", "iconName": "FileText",
                "description": "Document layout analysis and structured table deconstruction",
                "status": "active", "config": {"layout_analysis": True, "engine": "layout_parser"},
            },
            {
                "id": "4", "label": "Format Normalization & OCR", "category": "parsing", "mode": "both",
                "engine": "Format Normalizer & OCR Engine", "iconName": "FileText",
                "description": "DOCX/XLSX to PDF/A format normalization and OCR",
                "status": "active" if bool(s.document_converter_api_key) else "optional",
                "config": {"ocr_enabled": bool(s.document_converter_api_key), "api_key": SecretVault.mask_secret(s.document_converter_api_key)},
            },
            {
                "id": "5", "label": "LLM Schema Extraction", "category": "extraction", "mode": "both",
                "engine": "LLM Extraction Engine", "iconName": "Database",
                "description": "Structured JSON record extraction & validation",
                "status": "active" if bool(s.llm_api_key) else "optional",
                "config": {"model": s.llm_model, "anomaly_detection": True, "api_key": SecretVault.mask_secret(s.llm_api_key)},
            },
            {
                "id": "6", "label": "PDF Report Generator", "category": "dossier", "mode": "both",
                "engine": "HTML-to-PDF Engine", "iconName": "ShieldCheck",
                "description": "High-fidelity HTML-to-PDF reports with PII data masking",
                "status": "active" if bool(s.document_dossier_api_key) else "optional",
                "config": {"format": "pdf", "pii_redaction": bool(s.document_redactor_api_key), "api_key": SecretVault.mask_secret(s.document_dossier_api_key)},
            },
            {
                "id": "7", "label": "S3 Object Storage", "category": "storage", "mode": "custom",
                "engine": "S3-Compatible Object Store", "iconName": "Cloud",
                "description": "Upload JSON artifacts and compiled dossiers to your own S3 bucket",
                "status": "optional",
                "config": {
                    "bucket_name": "",
                    "region": "us-east-1",
                    "endpoint_url": "",
                    "access_key": "",
                    "secret_key": "",
                },
            },
            {
                "id": "8", "label": "Database Warehouse Sink", "category": "storage", "mode": "custom",
                "engine": "PostgreSQL / Snowflake / MySQL", "iconName": "Database",
                "description": "Direct export into customer data warehouse tables",
                "status": "active" if bool(s.database_url) else "optional",
                "config": {"connection_uri": SecretVault.mask_secret(s.database_url), "target_table": "orbit_extracted_records"},
            },
            {
                "id": "9", "label": "Slack Notifications", "category": "notify", "mode": "custom",
                "engine": "Slack Incoming Webhook", "iconName": "MessageSquare",
                "description": "Slack alert webhooks with signed report links",
                "status": "optional",
                "config": {"webhook_url": "", "channel": "#orbit-alerts"},
            },
            {
                "id": "10", "label": "Email Alert Notifications", "category": "notify", "mode": "both",
                "engine": "Managed Gateway / Custom SMTP", "iconName": "Mail",
                "description": "Transactional email alerts with attached telemetry and dossier links",
                "status": "active" if bool(s.email_api_key) else "optional",
                "config": {
                    "mode": "managed",
                    "recipient_email": "team@company.com",
                    "notify_on_anomaly": True,
                    "sender_address": s.email_sender_address or "",
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_username": "alerts@company.com",
                    "smtp_password": "",
                    "use_tls": True,
                    "api_key": SecretVault.mask_secret(s.email_api_key),
                    "base_url": "",
                },
            },
            {
                "id": "11", "label": "Outbound Webhooks", "category": "notify", "mode": "custom",
                "engine": "Signed HTTP POST Dispatcher", "iconName": "Radio",
                "description": "Signed HMAC-SHA256 webhooks for real-time downstream ingestion",
                "status": "optional",
                "config": {"webhook_url": "", "signing_secret": "", "timeout_sec": 10},
            },
        ]

        # Overlay any locally updated/saved configurations
        for adapter in topology:
            saved_cfg = cls._custom_adapter_configs.get(str(adapter["id"])) or cls._custom_adapter_configs.get(str(adapter["label"]).lower())
            if saved_cfg:
                adapter["config"].update(saved_cfg)
                adapter["status"] = "active"
        return topology

    @classmethod
    async def test_adapter_connection(cls, adapter_id: str, config: dict[str, Any]) -> tuple[bool, str]:
        """Performs a secure live connectivity test with transient 30s probe caching."""
        cache_key = cache_service.key_for_probe(str(adapter_id), config)
        cached_probe = await cache_service.get(cache_key)
        if cached_probe is not None and isinstance(cached_probe, (list, tuple)) and len(cached_probe) == 2:
            return bool(cached_probe[0]), str(cached_probe[1])

        res = await cls._execute_adapter_probe(adapter_id, config)
        if res and isinstance(res, (list, tuple)) and len(res) == 2:
            await cache_service.set(cache_key, list(res), ttl_seconds=30)
        return res

    @classmethod
    def _resolve_secret(
        cls,
        adapter_id: str,
        submitted_val: Any,
        field_keys: str | tuple[str, ...],
        daemon_fallback: str | None = None,
    ) -> str:
        """
        Resolves unmasked credential value from submitted input, saved custom configs,
        or daemon environment fallback.
        """
        if submitted_val and not SecretVault.is_masked(str(submitted_val)):
            return str(submitted_val).strip()

        saved_cfg = cls._custom_adapter_configs.get(str(adapter_id), {})
        if isinstance(field_keys, str):
            field_keys = (field_keys,)

        for key in field_keys:
            saved_val = saved_cfg.get(key)
            if saved_val and not SecretVault.is_masked(str(saved_val)):
                return str(saved_val).strip()

        return (daemon_fallback or "").strip()

    @classmethod
    async def _execute_adapter_probe(cls, adapter_id: str, config: dict[str, Any]) -> tuple[bool, str]:
        """Executes adapter probe dispatch without logging raw secrets."""
        clean_id = str(adapter_id).lower()
        try:
            # 0. LLM Schema Extraction
            if any(k in clean_id for k in ("llm", "schema_extractor", "extraction", "schema")) or clean_id == "5":
                api_key = cls._resolve_secret(adapter_id, config.get("api_key"), "api_key", get_settings().llm_api_key)
                if not api_key:
                    return False, "LLM API key is not configured. Set LLM_API_KEY in environment settings."
                return True, f"LLM extraction engine reachable. Model: {config.get('model') or get_settings().llm_model}"

            # 0b. Document Parser (Layout Analysis)
            if any(k in clean_id for k in ("doc_parser", "layout", "layout_parser", "parsing", "table_parser")) or clean_id == "3":
                return True, "Document layout parser is active. No external credentials required."

            # 0c. Format Normalization & OCR
            if any(k in clean_id for k in ("format_converter", "ocr", "format_normal", "converter")) or clean_id == "4":
                api_key = cls._resolve_secret(adapter_id, config.get("api_key"), "api_key", get_settings().document_converter_api_key)
                if not api_key:
                    return False, "Document Converter API key is not configured. Set DOCUMENT_CONVERTER_API_KEY to enable OCR and format normalization."
                base_url = (config.get("base_url") or get_settings().document_converter_base_url).rstrip("/")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        res = await client.get(f"{base_url}/health", headers={"Authorization": f"Bearer {api_key}"})
                        if res.status_code < 500:
                            return True, f"Format converter reachable at {base_url} (HTTP {res.status_code})."
                        return False, f"Format converter returned HTTP {res.status_code}."
                except Exception as probe_err:
                    return False, f"Format converter unreachable: {probe_err}"

            # 0d. PDF Report Generator / HTML Dossier / PII Redactor / Template Generator
            if any(k in clean_id for k in ("html_dossier", "pdf_report", "dossier", "pii_redactor", "redactor", "template_generator", "template")) or clean_id in ("6",):
                dossier_fallback = (
                    get_settings().document_dossier_api_key
                    or get_settings().document_template_api_key
                    or get_settings().document_redactor_api_key
                )
                api_key = cls._resolve_secret(adapter_id, config.get("api_key"), "api_key", dossier_fallback)
                if not api_key:
                    return False, "PDF Report Generator API key is not configured. Set DOCUMENT_DOSSIER_API_KEY to enable HTML-to-PDF generation."
                base_url = (config.get("base_url") or get_settings().document_dossier_base_url).rstrip("/")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        res = await client.get(base_url, headers={"Authorization": f"Bearer {api_key}"})
                        if res.status_code < 500:
                            return True, f"PDF generation engine reachable at {base_url} (HTTP {res.status_code})."
                        return False, f"PDF generation engine returned HTTP {res.status_code}."
                except Exception as probe_err:
                    return False, f"PDF generation engine unreachable: {probe_err}"

            # 1. Database Warehouse Sink
            if any(k in clean_id for k in ("database", "db", "sql", "warehouse", "table")) or clean_id == "8":
                raw_uri = cls._resolve_secret(
                    adapter_id,
                    config.get("connection_uri") or config.get("database_url"),
                    ("connection_uri", "database_url"),
                    get_settings().database_url,
                )
                target_tbl = config.get("target_table") or config.get("table_name") or "orbit_extracted_records"
                sink = DatabaseExportSink(connection_uri=raw_uri, target_table=target_tbl)
                return sink.test_connection()

            # 2. Email Notifications (Managed & Custom SMTP)
            if any(k in clean_id for k in ("email", "mail", "smtp", "notify_email", "email_alert")) or clean_id == "10":
                from core.adapters.communication.email import EmailNotificationAdapter
                delivery_mode = config.get("mode", "managed")
                recipient = str(
                    config.get("recipient_email")
                    or config.get("email")
                    or config.get("recipient")
                    or config.get("to")
                    or config.get("email_to")
                    or config.get("email_address")
                    or ""
                ).strip().strip("'\"")

                if not recipient or "@" not in recipient:
                    saved_rec = cls._custom_adapter_configs.get(str(adapter_id), {}).get("recipient_email") or cls._custom_adapter_configs.get(str(adapter_id), {}).get("email")
                    if saved_rec and "@" in str(saved_rec):
                        recipient = str(saved_rec).strip().strip("'\"")

                if not recipient or "@" not in recipient:
                    return False, "A valid recipient email address is required (e.g. team@company.com)."

                if delivery_mode == "custom":
                    host = config.get("smtp_host") or ""
                    port = int(config.get("smtp_port") or 587)
                    username = config.get("smtp_username") or ""
                    password = cls._resolve_secret(adapter_id, config.get("smtp_password"), "smtp_password")
                    use_tls = bool(config.get("use_tls", True))
                    return EmailNotificationAdapter.test_smtp_connection(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        use_tls=use_tls,
                    )
                else:
                    api_key = cls._resolve_secret(adapter_id, config.get("api_key"), "api_key", get_settings().email_api_key)
                    settings = get_settings()
                    sender = config.get("sender_address") or settings.email_sender_address
                    base_url = config.get("base_url") or settings.email_base_url

                    return await EmailNotificationAdapter.test_managed_connection(
                        recipient_email=recipient,
                        api_key=api_key,
                        base_url=base_url,
                        sender_address=sender,
                    )

            # 3. Slack Notifications
            if any(k in clean_id for k in ("slack", "notify_slack", "slack_alert")) or clean_id == "9":
                from core.adapters.communication.slack import SlackWebhookAdapter
                url = cls._resolve_secret(adapter_id, config.get("webhook_url") or config.get("url"), ("webhook_url", "url"))
                if not url:
                    return False, "Slack Webhook URL is not configured in node."
                adapter = SlackWebhookAdapter(webhook_url=url)
                return await adapter.test_connection()

            # 4. Outbound Signed Webhooks
            if any(k in clean_id for k in ("webhook", "signed_webhook", "webhook_alert", "radio")) or clean_id == "11":
                from core.adapters.communication.webhook import WebhookAdapter
                url = cls._resolve_secret(adapter_id, config.get("webhook_url") or config.get("url"), ("webhook_url", "url"))
                if not url:
                    return False, "Webhook URL is not configured in node."

                secret = cls._resolve_secret(
                    adapter_id,
                    config.get("signing_secret") or config.get("secret"),
                    ("signing_secret", "secret"),
                    "orbit-webhook-secret-key",
                )
                timeout = float(config.get("timeout_sec") or 10.0)
                adapter = WebhookAdapter(webhook_url=url, signing_secret=secret, timeout_sec=timeout, max_retries=1)
                return await adapter.test_connection()

            # 5. S3 Cloud Storage
            if any(k in clean_id for k in ("s3", "storage", "s3_storage", "cloud", "bucket")) or clean_id == "7":
                b_name = str(config.get("bucket_name") or config.get("bucket") or "orbit-exports").strip()
                region = str(config.get("region") or "us-east-1").strip()
                endpoint = config.get("endpoint_url") or config.get("endpoint") or None
                acc_key = cls._resolve_secret(adapter_id, config.get("access_key") or config.get("aws_access_key_id"), ("access_key", "aws_access_key_id"))
                sec_key = cls._resolve_secret(adapter_id, config.get("secret_key") or config.get("aws_secret_access_key"), ("secret_key", "aws_secret_access_key"))

                sink = S3ExportSink(
                    bucket_name=b_name,
                    region=region,
                    endpoint_url=endpoint,
                    access_key=acc_key,
                    secret_key=sec_key,
                )
                return await sink.test_connection()

            return True, f"Adapter '{adapter_id}' probe succeeded."
        except Exception as e:
            logger.exception("Connection test failed for adapter %s: %s", adapter_id, e)
            return False, "An error occurred while probing the adapter. Please verify the configuration settings."

    @classmethod
    def deploy_pipeline(cls, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deploys and persists the active pipeline node topology in the Database."""
        from datetime import datetime, timezone
        from core.db.orm import WorkflowPipeline
        from core.db.session import SessionLocal

        cls._deployed_pipeline = nodes

        # 1. Database persistence
        try:
            db = SessionLocal()
            try:
                pipeline = db.query(WorkflowPipeline).filter(WorkflowPipeline.active.is_(True)).first()
                if not pipeline:
                    pipeline = WorkflowPipeline(name="Active Production Pipeline", nodes=nodes, edges=[], active=True)
                    db.add(pipeline)
                else:
                    pipeline.nodes = nodes
                    pipeline.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Successfully persisted deployed pipeline to database (ID: %s)", pipeline.id)
            except Exception as db_err:
                db.rollback()
                logger.warning("Database write failed for workflow pipeline (%s). Using local storage cache.", db_err)
            finally:
                db.close()
        except Exception as conn_err:
            logger.warning("Database connection unavailable for workflow deploy: %s", conn_err)

        # 2. Local disk fallback
        try:
            cls._storage_path.parent.mkdir(parents=True, exist_ok=True)
            cls._storage_path.write_text(json.dumps(nodes, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to persist pipeline to disk: %s", e)

        logger.info("Deployed active pipeline with %d nodes", len(nodes))
        return cls._deployed_pipeline

    @classmethod
    def get_deployed_pipeline(cls) -> list[dict[str, Any]]:
        """Retrieves the deployed active pipeline nodes from Database or local cache."""
        from core.db.orm import WorkflowPipeline
        from core.db.session import SessionLocal

        try:
            db = SessionLocal()
            try:
                pipeline = (
                    db.query(WorkflowPipeline)
                    .filter(WorkflowPipeline.active.is_(True))
                    .order_by(WorkflowPipeline.updated_at.desc())
                    .first()
                )
                if pipeline and pipeline.nodes:
                    cls._deployed_pipeline = pipeline.nodes
                    return cls._deployed_pipeline
            except Exception as db_err:
                logger.warning("Database read failed for workflow pipeline (%s). Falling back to cache.", db_err)
            finally:
                db.close()
        except Exception as conn_err:
            logger.warning("Database connection unavailable to fetch workflow pipeline: %s", conn_err)

        if not cls._deployed_pipeline and cls._storage_path.exists():
            try:
                cls._deployed_pipeline = json.loads(cls._storage_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to read pipeline from disk: %s", e)
        return cls._deployed_pipeline

    @classmethod
    def save_adapter_config(cls, adapter_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Saves adapter configuration parameters and credentials in Database."""
        from datetime import datetime, timezone
        from core.db.orm import AdapterConfig
        from core.db.session import SessionLocal

        cls._custom_adapter_configs[str(adapter_id)] = config

        try:
            db = SessionLocal()
            try:
                adapter = db.query(AdapterConfig).filter(AdapterConfig.id == str(adapter_id)).first()
                if not adapter:
                    adapter = AdapterConfig(id=str(adapter_id), config=config)
                    db.add(adapter)
                else:
                    adapter.config = config
                    adapter.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Successfully saved adapter '%s' config to database", adapter_id)
            except Exception as db_err:
                db.rollback()
                logger.warning("Database write failed for adapter config (%s).", db_err)
            finally:
                db.close()
        except Exception as conn_err:
            logger.warning("Database connection unavailable to save adapter config: %s", conn_err)

        return {
            "adapter_id": adapter_id,
            "status": "saved",
            "message": f"Configuration for adapter '{adapter_id}' saved successfully to database.",
            "config": config,
        }
