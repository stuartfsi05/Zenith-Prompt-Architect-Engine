import json
from typing import Any, Optional


def parse_llm_json(raw_text: Optional[str]) -> Any:
    """Strips optional markdown code fences from an LLM string and parses JSON."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty LLM response")

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())
