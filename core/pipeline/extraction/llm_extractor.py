import json
from typing import Any

from core.llm.base import LLMClient
from core.llm.factory import get_llm_client
from core.llm.prompts import DYNAMIC_EXTRACTION_PROMPT
from core.models.execution_plan import ExecutionPlan


class LLMExtractor:
    """Schema-driven LLM extraction that adapts to any entity schema."""

    _llm: LLMClient | None

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def extract(
        self, url: str, content: str, plan: ExecutionPlan
    ) -> dict[str, Any]:
        if not content or not content.strip():
            return {"url": url, "extracted": False, "data": {}, "notes": "Empty content"}

        # Token cost safeguard: trim markdown content
        trimmed_content = content[:18000]

        schema_json = json.dumps(plan.extraction_schema.to_json_schema(), indent=2)

        user_prompt = (
            f"TARGET URL: {url}\n\n"
            f"TARGET ENTITY: {plan.extraction_schema.entity_name}\n\n"
            f"EXPECTED EXTRACTION SCHEMA:\n{schema_json}\n\n"
            f"PAGE CONTENT (markdown):\n{trimmed_content}"
        )

        try:
            raw = await self.llm.call_json(
                system_prompt=DYNAMIC_EXTRACTION_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            if not isinstance(raw, dict):
                raw = {}
            data = raw.get("data")
            if not isinstance(data, dict):
                data = {k: v for k, v in raw.items() if k not in ("extracted", "notes", "data")}
            extracted = bool(raw.get("extracted", True))
            return {
                "url": url,
                "extracted": extracted,
                "data": data,
                "notes": raw.get("notes"),
            }
        except Exception:  # noqa: BLE001
            return {
                "url": url,
                "extracted": False,
                "data": {},
                "notes": "Extraction could not parse entity schema from page content.",
            }
