"""Prototype blood-group rules used for OPERATIONAL candidate discovery only.

This table is a simplified demo rule for red-cell requests. It is NOT a clinical
compatibility decision: real compatibility and eligibility must be confirmed by
qualified medical professionals using official protocols.
"""

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]

# requested group -> donor groups the demo rule will consider
DEMO_COMPATIBLE_DONORS: dict[str, list[str]] = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

_ALIASES = {
    "positive": "+", "pos": "+", "plus": "+", "+ve": "+", "+": "+",
    "negative": "-", "neg": "-", "minus": "-", "-ve": "-", "-": "-",
}


def normalize_blood_group(value: str | None) -> str | None:
    """Turn inputs like 'o neg', 'O-negative', 'ab +ve' into canonical 'O-', 'AB+'."""
    if not value:
        return None
    v = value.strip().upper().replace(" ", "").replace("_", "")
    for group in ("AB", "A", "B", "O"):
        if v.startswith(group):
            rest = v[len(group):].lower()
            sign = _ALIASES.get(rest)
            if sign is None:
                for k, s in _ALIASES.items():
                    if rest == k or rest.startswith(k):
                        sign = s
                        break
            if sign:
                return f"{group}{sign}"
            return None
    return None


def candidate_groups(requested: str) -> list[str]:
    return DEMO_COMPATIBLE_DONORS.get(requested, [requested])
