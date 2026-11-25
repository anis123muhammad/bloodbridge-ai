"""Priority Manager.

Transparent, rule-based OPERATIONAL priority for the work queue. This is not
clinical triage; it only orders requests using requester-selected urgency,
time to deadline and size of the request.
"""
from typing import Any

from app.models import BloodRequest
from app.utils.time import as_aware, utcnow

URGENCY_POINTS = {"critical": 60, "urgent": 40, "normal": 15}
LEVEL_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _deadline_points(hours_left: float) -> tuple[int, str]:
    if hours_left <= 2:
        return 30, f"deadline in {hours_left:.1f} h (<= 2 h: +30)"
    if hours_left <= 6:
        return 20, f"deadline in {hours_left:.1f} h (<= 6 h: +20)"
    if hours_left <= 24:
        return 10, f"deadline in {hours_left:.1f} h (<= 24 h: +10)"
    return 0, f"deadline in {hours_left:.0f} h (> 24 h: +0)"


def calculate_priority(req: BloodRequest) -> dict[str, Any]:
    hours_left = max((as_aware(req.deadline) - utcnow()).total_seconds() / 3600, 0)
    urgency_pts = URGENCY_POINTS.get(req.urgency, 15)
    deadline_pts, deadline_text = _deadline_points(hours_left)
    units_pts = 10 if req.units_requested >= 3 else 0

    score = urgency_pts + deadline_pts + units_pts
    if score >= 80:
        level = "critical"
    elif score >= 55:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    parts = [f"urgency '{req.urgency}' (+{urgency_pts})", deadline_text]
    if units_pts:
        parts.append(f"{req.units_requested} units requested (>= 3: +10)")
    reason = f"Priority {level} (score {score}/100): " + "; ".join(parts) + "."

    return {
        "priority": level,
        "score": score,
        "reason": reason,
        "rule": "score = urgency points + deadline points + size points; "
        ">=80 critical, >=55 high, >=30 medium, else low",
    }
