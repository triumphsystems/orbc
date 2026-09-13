"""Shared utilities for LLM response parsing across all provider adapters."""

import json
import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def strip_json_fences(text: str) -> str:
    """Removes markdown code fences from LLM responses."""
    return _JSON_FENCE_RE.sub("", text).strip()


def parse_llm_json(content: str) -> dict[str, Any]:
    """Parse JSON from LLM output with fallback heuristics.

    Handles common LLM quirks: markdown fences, leading text, trailing commas.
    """
    cleaned = strip_json_fences(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Fallback: attempt to find first '{' and last '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw output: {content[:400]}")
