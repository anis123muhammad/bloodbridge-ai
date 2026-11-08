"""Follow-up Agent: tracks donor responses and keeps each request moving.

- analyze_donor_reply(): reads a donor's free-text reply (LLM, rules fallback) and
  flags anything staff should review. It never approves or rejects a donor.
- evaluate_request(): recounts responses, updates the request status, and when
  more donors are needed asks the matching agent for alternatives, which go back
  to a human for approval (no automatic outreach).
"""
import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ValidationError

from app.agents.llm import llm_json
from app.core.config import get_settings
from app.models import BloodRequest
from app.utils.time import as_aware, utcnow

REVIEW_KEYWORDS = ("fever", "sick", "ill", "cold", "flu", "infection", "medicine", "medication",
                   "antibiotic", "pregnan", "tattoo", "surgery", "travel", "malaria", "dengue",
                   "covid", "low hemoglobin", "weak", "dizzy")


class ReplyAnalysis(BaseModel):
    available_from: datetime | None = None
    concerns: list[str] = []
    summary: str | None = None


REPLY_PROMPT = """You read a blood donor's reply to a donation invitation for hospital staff.
Return ONLY JSON: {"available_from": ISO 8601 datetime with offset or null,
"concerns": [short phrases for anything health-related or logistical staff should check],
"summary": one short sentence}.
Do not judge eligibility. Do not invent details. Use null / [] when not stated."""


def _rule_reply(message: str) -> dict[str, Any]:
    lowered = message.lower()
    concerns = [w for w in REVIEW_KEYWORDS if w in lowered]
    available_from = None
    m = re.search(r"\b(?:after|from|at)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    if m:
        tz = ZoneInfo(get_settings().app_timezone)
        now = utcnow().astimezone(tz)
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm is None and hour < 8:  # "after 7" in an evening context usually means pm
            hour += 12
        if 0 <= hour <= 23:
            available_from = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if "tomorrow" in lowered or available_from < now - timedelta(hours=1):
                available_from += timedelta(days=1)
    return {"available_from": available_from, "concerns": concerns,
            "summary": message[:160]}


def analyze_donor_reply(message: str, deadline: datetime) -> dict[str, Any]:
    source = "rules"
    tz = ZoneInfo(get_settings().app_timezone)
    raw = llm_json(REPLY_PROMPT, f"Current time: {utcnow().astimezone(tz).isoformat()}\nReply:\n{message}")
    parsed = None
    if raw is not None:
        try:
            parsed = ReplyAnalysis.model_validate(raw)
            source = "llm"
        except ValidationError:
            parsed = None
    if parsed is None:
        parsed = ReplyAnalysis.model_validate(_rule_reply(message))

    available_from = as_aware(parsed.available_from)
    conflicts = bool(available_from and available_from > as_aware(deadline))
    return {
        "source": source,
        "available_from": available_from.isoformat() if available_from else None,
        "concerns": parsed.concerns,
        "summary": parsed.summary,
        "conflicts_with_deadline": conflicts,
        "needs_staff_review": bool(parsed.concerns) or conflicts,
    }


def response_counts(req: BloodRequest) -> dict[str, int]:
    counts = {"accepted": 0, "accepted_at_risk": 0, "declined": 0, "pending": 0, "expired": 0}
    for inv in req.invitations:
        if inv.status == "accepted":
            if (inv.response_analysis or {}).get("conflicts_with_deadline"):
                counts["accepted_at_risk"] += 1
            else:
                counts["accepted"] += 1
        elif inv.status in counts:
            counts[inv.status] += 1
    counts["units_requested"] = req.units_requested
    counts["still_needed"] = max(req.units_requested - counts["accepted"], 0)
    counts["suggested_awaiting_approval"] = sum(1 for m in req.matches if m.status == "suggested")
    return counts


def decide_next_status(req: BloodRequest, counts: dict[str, int]) -> tuple[str, str, bool]:
    """Return (new_status, note, needs_alternatives). Pure rules; easy to test."""
    if counts["still_needed"] == 0:
        return ("fulfilled",
                "Workflow target reached: enough donors accepted. Acceptance is NOT a completed "
                "donation; hospital staff must confirm suitability and donation.", False)
    if counts["accepted"] > 0:
        status = "partially_fulfilled"
        note = f"{counts['accepted']} of {req.units_requested} donors accepted; {counts['still_needed']} still needed."
    else:
        status = "inviting_donors" if counts["pending"] else req.status
        note = f"{counts['pending']} invitation(s) pending; {counts['still_needed']} donor(s) still needed."
    if counts["accepted_at_risk"]:
        note += f" {counts['accepted_at_risk']} acceptance(s) arrive after the deadline and are not counted."

    # Pending invitations alone can no longer cover the gap -> more donors must be approved.
    gap = counts["still_needed"] - counts["pending"]
    needs_alternatives = False
    if gap > 0:
        if counts["suggested_awaiting_approval"] >= gap:
            status = "awaiting_approval"
            note += (f" {counts['suggested_awaiting_approval']} earlier suggestion(s) are still available; "
                     f"approve at least {gap} more donor(s).")
        else:
            needs_alternatives = True
    return status, note, needs_alternatives


def stale_invitation_cutoff() -> datetime:
    return utcnow() - timedelta(minutes=get_settings().invitation_timeout_minutes)
