"""Score one intake and enrichment payload. The model suggests a score; code checks the band."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Protocol

from risk_agent.scoring import band_from_score, deterministic_score

RISK_SYSTEM = """You score insurance risk from intake and enrichment.
Return one JSON object with these keys:
score (integer from 0 to 100, higher means riskier),
band (one of low, medium, high),
factors (array of short strings).
Use low under 35, medium from 35 through 74, and high from 75 up."""

REPAIR_USER = (
    "Your previous response was not a JSON object. "
    "Return only one JSON object and nothing else. Previous response:\n"
)


class ChatClient(Protocol):
    def chat(self, system: str, user: str) -> tuple:
        """Return raw text, prompt tokens, and completion tokens."""


class RiskAgentError(Exception):
    pass


def score_case(payload: Dict[str, Any], client: ChatClient) -> Dict[str, Any]:
    intake = payload.get("intake")
    enrichment = payload.get("enrichment")
    if not isinstance(intake, dict) or not isinstance(enrichment, dict):
        raise RiskAgentError("payload needs intake and enrichment objects")
    user = json.dumps({"intake": intake, "enrichment": enrichment})
    raw, prompt_tokens, completion_tokens = client.chat(RISK_SYSTEM, user)
    content = _parse_object(raw)
    if content is None:
        repair_raw, repair_prompt, repair_completion = client.chat(RISK_SYSTEM, REPAIR_USER + raw)
        prompt_tokens += repair_prompt
        completion_tokens += repair_completion
        content = _parse_object(repair_raw)
        if content is None:
            raise RiskAgentError("model returned invalid JSON after repair")
    llm_score = _optional_number(_field(content, "score"))
    if llm_score is None or llm_score < 0 or llm_score > 100:
        raise RiskAgentError("risk score must be an integer from 0 to 100")
    code_score = deterministic_score(enrichment)
    llm_band = band_from_score(llm_score)
    code_band = band_from_score(code_score)
    agreed = llm_band == code_band
    return {
        "score": max(llm_score, code_score) if agreed else None,
        "band": llm_band if agreed else None,
        "factors": _string_list(_field(content, "factors")),
        "llm_score": llm_score,
        "llm_band": llm_band,
        "deterministic_score": code_score,
        "deterministic_band": code_band,
        "agreed": agreed,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def _parse_object(raw: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _field(content: Dict[str, Any], name: str) -> Any:
    if name in content:
        return content[name]
    lowered = {str(key).lower(): value for key, value in content.items()}
    return lowered.get(name.lower())


def _optional_number(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if isinstance(item, str) and item.strip():
            items.append(item.strip())
        elif item is not None and not isinstance(item, (dict, list)):
            items.append(str(item))
    return items
