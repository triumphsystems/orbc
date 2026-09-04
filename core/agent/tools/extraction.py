import json
import logging
from typing import Any
from strands import tool

logger = logging.getLogger("core.agent.tools.extraction")


@tool
async def extract_structured_records(
    url: str,
    content: str,
    target_entity: str,
    expected_fields: list[str],
) -> list[dict[str, Any]]:
    """
    Extracts structured entity records from webpage content matching the target entity definition and expected fields.
    Returns a list of structured records found on the page.

    Args:
        url: The source URL where the content was retrieved.
        content: The text content or markdown snippet of the page.
        target_entity: The name of the entity being targeted (e.g. 'Research Paper', 'Grant', 'Job').
        expected_fields: The specific attribute fields to extract (e.g. ['title', 'authors', 'deadline']).
    """
    from core.llm.factory import get_llm_client
    from core.llm.prompts import DYNAMIC_EXTRACTION_PROMPT

    logger.info("Strands tool extract_structured_records: url='%s' entity='%s'", url, target_entity)
    trimmed_content = content[:18000]

    user_prompt = (
        f"TARGET URL: {url}\n\n"
        f"TARGET ENTITY: {target_entity}\n\n"
        f"EXPECTED FIELDS: {json.dumps(expected_fields)}\n\n"
        f"PAGE CONTENT:\n{trimmed_content}"
    )

    llm = get_llm_client()
    try:
        raw = await llm.call_json(
            system_prompt=DYNAMIC_EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
        )
        if isinstance(raw, list):
            return [{"url": url, "data": item, "valid": True} for item in raw if isinstance(item, dict)]
        elif isinstance(raw, dict):
            data = raw.get("data")
            if isinstance(data, list):
                return [{"url": url, "data": item, "valid": True} for item in data if isinstance(item, dict)]
            elif isinstance(data, dict):
                return [{"url": url, "data": data, "valid": True}]
            clean = {k: v for k, v in raw.items() if k not in ("extracted", "notes", "data")}
            return [{"url": url, "data": clean, "valid": bool(clean)}]
        return []
    except Exception as e:
        logger.warning("Strands extraction failed for %s: %s", url, e)
        return []
