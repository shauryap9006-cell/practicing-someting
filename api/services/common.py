"""Common helpers for API services and routers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import settings


def delay_color(delay_min: float) -> str:
    """Maps a delay to the dashboard traffic-light colour using configured thresholds."""
    if delay_min <= settings.DELAY_ON_TIME_MAX_MIN:
        return "green"
    if delay_min <= settings.DELAY_MODERATE_MAX_MIN:
        return "amber"
    return "red"


def format_metric(source: Dict[str, Any], key: str, digits: int = 2) -> Optional[float]:
    """Safely extracts and rounds numeric metric values."""
    value = source.get(key)
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None
