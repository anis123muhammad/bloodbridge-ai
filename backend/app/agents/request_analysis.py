"""Request Analysis Agent.

Turns hospital input into a structured, validated request.
- analyze_text(): free text -> structured fields (LLM first, rules as fallback).
- analyze_request(): validates a saved request before the workflow continues.

The LLM may only extract what the text says. Missing facts are reported as
missing, never invented, and every extracted value is re-validated here.
"""
import re
from datetime import datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ValidationError, field_validator

from app.agents.llm import llm_json
from app.core.config import get_settings
from app.models import BloodRequest
from app.services.blood_rules import BLOOD_GROUPS, normalize_blood_group
from app.services.geo import lookup_city
from app.utils.time import as_aware, utcnow

REQUIRED_FIELDS = ["blood_group", "units_requested", "urgency", "location", "deadline"]


class ExtractedRequest(BaseModel):
    """Schema the LLM output must satisfy. Everything optional: missing stays missing."""

    blood_group: str | None = None
    units_requested: int | None = None
    urgency: Literal["normal", "urgent", "critical"] | None = None
    location: str | None = None
    deadline: datetime | None = None
    notes: str | None = None

    @field_validator("blood_group")
    @classmethod
    def validate_bg(cls, v: str | None) -> str | None:
        g = normalize_blood_group(v) if v else None
        return g if g in BLOOD_GROUPS else None

    @field_validator("units_requested")
    @classmethod
    def validate_units(cls, v: int | None) -> int | None:
        return v if v is not None and 1 <= v <= 20 else None


SYSTEM_PROMPT = """You extract blood-request details from hospital messages for an operations tool.
Return ONLY a JSON object with these keys:
  blood_group (one of O-, O+, A-, A+, B-, B+, AB-, AB+ or null),
  units_requested (integer or null),
  urgency ("normal", "urgent", "critical" or null),
  location (city or hospital area as written, or null),
  deadline (ISO 8601 datetime with timezone offset, or null),
  notes (short summary of any other operational detail, or null).
Rules: never guess. If a value is not stated in the message, use null.
Use "critical" only for life-threatening wording (emergency, ICU, accident, trauma, surgery now).
Resolve relative times ("tonight", "by 6pm", "in 3 hours") using the current time given."""

_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                 "seven": 7, "eight": 8, "nine": 9, "ten": 10, "a": 1, "an": 1}
_BG_RE = re.compile(
    r"\b(AB|A|B|O)[\s-]*(\+ve|-ve|positive|negative|pos|neg|\+|-)(?![a-z])", re.IGNORECASE
)
_UNITS_RE = re.compile(
    r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+"
    r"(?:\w+\s+){0,2}?(?:units?|bags?|pints?|bottles?)\b",
    re.IGNORECASE,
)
# e.g. "need 2 O neg" (a number directly before a blood group)
_UNITS_BG_RE = re.compile(
    r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:units?\s+(?:of\s+)?)?"
    r"(?:AB|A|B|O)\s*(?:\+|-|pos|neg)",
    re.IGNORECASE,
)
_CRITICAL_WORDS = ("critical", "emergency", "icu", "accident", "trauma", "life-threatening",
                   "rta", "bleeding", "surgery now", "immediately")
_URGENT_WORDS = ("urgent", "urgently", "asap", "today", "tonight", "quickly", "soon")


def _local_now() -> datetime:
    return utcnow().astimezone(ZoneInfo(get_settings().app_timezone))


def _parse_deadline(text: str) -> datetime | None:
    """Rule-based deadline parsing for common phrases. Returns tz-aware datetime or None."""
    now = _local_now()
    t = text.lower()
    m = re.search(r"\bin\s+(\d{1,2})\s*(hours?|hrs?|h)\b", t)
    if m:
        return now + timedelta(hours=int(m.group(1)))
    m = re.search(r"\bin\s+(\d{1,3})\s*(minutes?|mins?)\b", t)
    if m:
        return now + timedelta(minutes=int(m.group(1)))
    m = re.search(r"\b(?:by|before|until|till)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t)
    if m:
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if "tomorrow" in t or target <= now:
                target += timedelta(days=1)
            return target
    if "tonight" in t:
        return now.replace(hour=23, minute=0, second=0, microsecond=0)
    if "tomorrow" in t:
        return (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    if "today" in t:
        return now.replace(hour=23, minute=0, second=0, microsecond=0)
    return None


def _rule_extract(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = _BG_RE.search(text)
    if m:
        out["blood_group"] = normalize_blood_group(m.group(1) + m.group(2))
    m = _UNITS_RE.search(text) or _UNITS_BG_RE.search(text)
    if m:
        raw = m.group(1).lower()
        out["units_requested"] = int(raw) if raw.isdigit() else _WORD_NUMBERS.get(raw)
    lowered = text.lower()
    if any(w in lowered for w in _CRITICAL_WORDS):
        out["urgency"] = "critical"
    elif any(w in lowered for w in _URGENT_WORDS):
        out["urgency"] = "urgent"
    city = lookup_city(text)
    if city:
        out["location"] = city[0]
    deadline = _parse_deadline(text)
    if deadline:
        out["deadline"] = deadline
    return out


def analyze_text(text: str, default_location: str | None = None) -> dict[str, Any]:
    """Free text -> structured fields + list of missing fields. Saves nothing."""
    source = "rules"
    fields: dict[str, Any] = {}
    llm_raw = llm_json(
        SYSTEM_PROMPT,
        f"Current time: {_local_now().isoformat()}\nMessage:\n{text}",
    )
    if llm_raw is not None:
        try:
            parsed = ExtractedRequest.model_validate(llm_raw)
            fields = parsed.model_dump(exclude_none=True)
            source = "llm"
        except ValidationError:
            fields = {}
    if source == "rules":
        fields = ExtractedRequest.model_validate(_rule_extract(text)).model_dump(exclude_none=True)
    else:
        # fill any gaps the LLM left with deterministic rules (still never invented)
        for k, v in ExtractedRequest.model_validate(_rule_extract(text)).model_dump(exclude_none=True).items():
            fields.setdefault(k, v)

    notes = []
    if "location" not in fields and default_location:
        fields["location"] = default_location
        notes.append(f"Location not stated; defaulted to the hospital's city ({default_location}).")
    if "urgency" not in fields:
        fields["urgency"] = "normal"
        notes.append("No urgency wording found; set to 'normal'. Please confirm.")

    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    return {
        "fields": fields,
        "missing_fields": missing,
        "validation_status": "valid" if not missing else "incomplete",
        "source": source,
        "notes": notes,
    }


def analyze_request(req: BloodRequest) -> dict[str, Any]:
    """Validate a saved request. Deterministic; optionally cross-checks the description."""
    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, Any] = {}

    bg = normalize_blood_group(req.blood_group)
    if bg not in BLOOD_GROUPS:
        errors.append(f"Unknown blood group '{req.blood_group}'.")
    else:
        normalized["blood_group"] = bg
    if not 1 <= (req.units_requested or 0) <= 20:
        errors.append("Units requested must be between 1 and 20.")
    if req.urgency not in ("normal", "urgent", "critical"):
        errors.append("Urgency must be normal, urgent or critical.")
    deadline = as_aware(req.deadline)
    if deadline is None:
        errors.append("Deadline is required.")
    elif deadline <= utcnow():
        errors.append("Deadline has already passed.")
    if not (req.location or "").strip():
        errors.append("Location is required.")
    else:
        city = lookup_city(req.location)
        if city:
            normalized["location_city"] = city[0]
        else:
            warnings.append(
                f"Location '{req.location}' is not in the city table; the hospital's coordinates will be used."
            )

    # Cross-check free-text description against the structured fields
    if req.description:
        extracted = analyze_text(req.description)["fields"]
        if extracted.get("blood_group") and bg and extracted["blood_group"] != bg:
            warnings.append(
                f"Description mentions {extracted['blood_group']} but the form says {bg}. Please confirm."
            )
        if extracted.get("units_requested") and extracted["units_requested"] != req.units_requested:
            warnings.append(
                f"Description mentions {extracted['units_requested']} unit(s) but the form says "
                f"{req.units_requested}. Please confirm."
            )
        if extracted.get("urgency") == "critical" and req.urgency != "critical":
            warnings.append("Description sounds critical but urgency is not set to critical.")

    return {
        "validation_status": "valid" if not errors else "invalid",
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }
