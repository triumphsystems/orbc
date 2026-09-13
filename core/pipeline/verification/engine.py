import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from core.models.enums import Frequency
from core.models.execution_plan import ExecutionPlan

logger = logging.getLogger("core.pipeline.verification")


@dataclass
class VerificationReport:
    """
    Structured outcome of Orbit's verification engine answering the 7 core questions:
    1. Were sources discovered?
    2. Were the expected pages retrieved?
    3. Was the required information extracted?
    4. Did the data pass validation?
    5. Were the results persisted?
    6. Was the workflow completed successfully?
    7. When is the next execution?
    """

    verified: bool
    sources_discovered: bool
    sources_count: int
    pages_retrieved: bool
    pages_count: int
    data_extracted: bool
    extracted_count: int
    data_validated: bool
    validated_count: int
    results_persisted: bool
    next_execution_scheduled: bool
    summary: str
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VerificationEngine:
    """Evaluates run integrity against quality thresholds and operational completeness."""

    def verify_run(
        self,
        plan: ExecutionPlan,
        sources: list[str],
        pages: Mapping[str, str | None],
        extracted_records: list[dict[str, Any]],
        validated_records: list[dict[str, Any]],
        results_persisted: bool,
        next_run_at: Any = None,
    ) -> VerificationReport:
        sources_discovered = len(sources) > 0
        successful_pages = [p for p in pages.values() if p and len(p.strip()) > 0]
        pages_retrieved = len(successful_pages) > 0
        data_extracted = len(extracted_records) > 0
        data_validated = len(validated_records) > 0

        # Recurring plans must have next_run_at scheduled
        is_recurring = plan.frequency != Frequency.once
        next_scheduled = (next_run_at is not None) if is_recurring else True

        # Pipeline is verified when data extraction and validation successfully yield clean records
        is_verified = (
            sources_discovered
            and pages_retrieved
            and data_extracted
            and data_validated
            and results_persisted
            and next_scheduled
        )

        checks = {
            "sources_discovered": sources_discovered,
            "pages_retrieved": pages_retrieved,
            "data_extracted": data_extracted,
            "data_validated": data_validated,
            "results_persisted": results_persisted,
            "next_execution_scheduled": next_scheduled,
        }

        if is_verified:
            summary = (
                f"Verification Passed: {len(validated_records)}/{len(extracted_records)} records verified "
                f"across {len(sources)} sources with complete persistence."
            )
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            summary = f"Verification Warning: Incomplete checks: {', '.join(failed_checks)}"

        logger.info(f"Verification Engine Outcome: {summary}")

        return VerificationReport(
            verified=is_verified,
            sources_discovered=sources_discovered,
            sources_count=len(sources),
            pages_retrieved=pages_retrieved,
            pages_count=len(successful_pages),
            data_extracted=data_extracted,
            extracted_count=len(extracted_records),
            data_validated=data_validated,
            validated_count=len(validated_records),
            results_persisted=results_persisted,
            next_execution_scheduled=next_scheduled,
            summary=summary,
            checks=checks,
        )
