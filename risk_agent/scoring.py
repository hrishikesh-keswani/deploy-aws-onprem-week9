"""Deterministic bureau score. The model does not choose this number."""

from __future__ import annotations

from typing import Any, Dict, Optional

HIGH_SCORE_MIN = 75
MEDIUM_SCORE_MIN = 35
_BASE_SCORE = 20
_CLAIM_POINTS = 15
_FLOOD_POINTS = 25
_UNKNOWN_POINTS = 15
_CREDIT_POINTS = {
    "excellent": 0,
    "good": 5,
    "fair": 20,
    "poor": 35,
    "unknown": _UNKNOWN_POINTS,
}
_OCCUPATION_POINTS = {
    "low": 0,
    "medium": 10,
    "high": 25,
    "unknown": _UNKNOWN_POINTS,
}


def deterministic_score(enrichment: Dict[str, Any]) -> int:
    """Score the bureau row with the Week 8 point table, capped at 100."""
    bureau = enrichment.get("bureau")
    if not isinstance(bureau, dict):
        bureau = {}
    claims = _optional_number(bureau.get("prior_claims")) or 0
    if claims < 0:
        claims = 0
    credit = _label(bureau.get("credit_band"))
    occupation = _label(bureau.get("occupation_class"))
    total = _BASE_SCORE + (claims * _CLAIM_POINTS)
    total += _CREDIT_POINTS.get(credit, _UNKNOWN_POINTS)
    total += _OCCUPATION_POINTS.get(occupation, _UNKNOWN_POINTS)
    if bureau.get("flood_zone") is True:
        total += _FLOOD_POINTS
    if total > 100:
        return 100
    return total


def band_from_score(score: int) -> str:
    if score >= HIGH_SCORE_MIN:
        return "high"
    if score >= MEDIUM_SCORE_MIN:
        return "medium"
    return "low"


def _optional_number(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if not cleaned or cleaned.lower() in {"null", "none", "unknown", "n/a"}:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


def _label(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    return value.strip().lower()
