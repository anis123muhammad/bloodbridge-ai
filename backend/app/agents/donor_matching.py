"""Donor Matching Agent.

Deterministic SQL filters plus a transparent score over SYNTHETIC donor records.
The score is an operational ranking for staff review. It is not medical
compatibility or eligibility; staff must verify suitability.
"""
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BloodRequest, Donor, DonorMatch, Invitation, User
from app.services.blood_rules import candidate_groups
from app.services.geo import haversine_km, lookup_city

ACTIVE_STATUSES = ("submitted", "processing", "awaiting_approval", "inviting_donors", "partially_fulfilled")


def request_coordinates(req: BloodRequest) -> tuple[float, float] | None:
    city = lookup_city(req.location)
    if city:
        return city[1]
    if req.hospital and req.hospital.latitude is not None:
        return req.hospital.latitude, req.hospital.longitude
    return None


def _days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        return (date.today() - date.fromisoformat(iso_date[:10])).days
    except ValueError:
        return None


def find_matching_donors(
    db: Session,
    req: BloodRequest,
    exclude_donor_ids: set[uuid.UUID] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Return ranked candidates, widening the radius step by step until enough are found."""
    s = get_settings()
    limit = limit or s.max_candidates
    exclude = set(exclude_donor_ids or set())
    groups = candidate_groups(req.blood_group)
    origin = request_coordinates(req)

    # Donors already holding a pending invitation for ANOTHER active request are busy.
    busy = set(
        db.scalars(
            select(Invitation.donor_id)
            .join(BloodRequest, Invitation.request_id == BloodRequest.id)
            .where(
                Invitation.status == "pending",
                Invitation.request_id != req.id,
                BloodRequest.status.in_(ACTIVE_STATUSES),
            )
        )
    )

    # SQL filters: blood-group demo rule + availability
    rows = db.execute(
        select(Donor, User.name)
        .join(User, Donor.user_id == User.id)
        .where(Donor.blood_group.in_(groups), Donor.availability == "available")
    ).all()

    filtered_out = {"excluded_already_contacted": 0, "busy_other_request": 0,
                    "demo_eligibility": 0, "recent_donation": 0, "no_location": 0}
    pool = []
    for donor, name in rows:
        if donor.id in exclude:
            filtered_out["excluded_already_contacted"] += 1
            continue
        if donor.id in busy:
            filtered_out["busy_other_request"] += 1
            continue
        elig = donor.demo_eligibility or {}
        if elig.get("status", "eligible_demo") != "eligible_demo":
            filtered_out["demo_eligibility"] += 1
            continue
        days = _days_since(elig.get("last_donation_date"))
        if days is not None and days < s.min_days_between_donations_demo:
            filtered_out["recent_donation"] += 1
            continue
        if origin and donor.latitude is not None:
            dist = haversine_km(origin[0], origin[1], donor.latitude, donor.longitude)
        elif lookup_city(donor.city) and lookup_city(req.location) and \
                lookup_city(donor.city)[0] == lookup_city(req.location)[0]:
            dist = 0.0
        else:
            filtered_out["no_location"] += 1
            continue
        pool.append((donor, name, dist, days))

    radius_used = s.radius_steps[-1]
    for radius in s.radius_steps:
        if sum(1 for p in pool if p[2] <= radius) >= min(limit, req.units_requested * 2):
            radius_used = radius
            break
    in_range = [p for p in pool if p[2] <= radius_used]

    candidates = []
    for donor, name, dist, days in in_range:
        reasons = []
        if donor.blood_group == req.blood_group:
            group_pts = 40
            reasons.append(f"Blood group {donor.blood_group} matches the request exactly (demo rule)")
        else:
            group_pts = 25
            reasons.append(f"Blood group {donor.blood_group} is accepted for {req.blood_group} under the demo rule")
        dist_pts = round(35 * max(0.0, 1 - dist / radius_used))
        reasons.append(f"About {dist:.1f} km away (within {radius_used:.0f} km search radius)")
        reasons.append("Marked available")
        if days is None:
            recency_pts = 8
            reasons.append("No previous donation on record (demo data)")
        else:
            recency_pts = round(15 * min(days, 365) / 365)
            reasons.append(f"Last demo donation {days} days ago")
        rate = float((donor.demo_eligibility or {}).get("response_rate", 0.5))
        response_pts = round(10 * max(0.0, min(rate, 1.0)))
        reasons.append(f"Past response rate {rate:.0%} (demo data)")
        score = group_pts + dist_pts + recency_pts + response_pts
        candidates.append({
            "donor_id": donor.id,
            "donor_name": name,
            "blood_group": donor.blood_group,
            "city": donor.city,
            "distance_km": round(dist, 1),
            "match_score": int(score),
            "reasons": reasons,
            "score_breakdown": {"blood_group": group_pts, "distance": dist_pts,
                                "recency": recency_pts, "responsiveness": response_pts},
        })

    candidates.sort(key=lambda c: (-c["match_score"], c["distance_km"]))
    return {
        "candidates": candidates[:limit],
        "radius_km": radius_used,
        "groups_considered": groups,
        "pool_size": len(rows),
        "in_radius": len(in_range),
        "filtered_out": filtered_out,
        "origin": origin,
    }


def save_matches(db: Session, req: BloodRequest, candidates: list[dict[str, Any]]) -> list[DonorMatch]:
    """Insert suggested matches, skipping donors already matched for this request (idempotent)."""
    existing = set(db.scalars(select(DonorMatch.donor_id).where(DonorMatch.request_id == req.id)))
    created = []
    for c in candidates:
        if c["donor_id"] in existing:
            continue
        m = DonorMatch(
            request_id=req.id,
            donor_id=c["donor_id"],
            match_score=c["match_score"],
            distance_km=c["distance_km"],
            match_reasons=c["reasons"],
            status="suggested",
        )
        db.add(m)
        created.append(m)
    db.flush()
    return created
