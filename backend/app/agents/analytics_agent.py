"""Analytics Agent: aggregates operational metrics. All figures are synthetic demo data."""
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentRun, BloodRequest, Donor, Invitation
from app.services.blood_rules import BLOOD_GROUPS

OPEN_STATUSES = ("submitted", "processing", "awaiting_approval", "inviting_donors", "partially_fulfilled")


def _req_scope(hospital_id: uuid.UUID | None):
    q = select(BloodRequest)
    return q.where(BloodRequest.hospital_id == hospital_id) if hospital_id else q


def overview(db: Session, hospital_id: uuid.UUID | None = None) -> dict[str, Any]:
    reqs = db.scalars(_req_scope(hospital_id)).all()
    inv_q = select(Invitation.status, func.count()).group_by(Invitation.status)
    if hospital_id:
        inv_q = inv_q.join(BloodRequest, Invitation.request_id == BloodRequest.id).where(
            BloodRequest.hospital_id == hospital_id
        )
    inv = dict(db.execute(inv_q).all())
    return {
        "demo_data": True,
        "total_donors": db.scalar(select(func.count()).select_from(Donor)) or 0,
        "available_donors": db.scalar(
            select(func.count()).select_from(Donor).where(Donor.availability == "available")
        ) or 0,
        "total_requests": len(reqs),
        "pending_requests": sum(1 for r in reqs if r.status in OPEN_STATUSES),
        "urgent_requests": sum(1 for r in reqs if r.urgency in ("urgent", "critical") and r.status in OPEN_STATUSES),
        "awaiting_approval": sum(1 for r in reqs if r.status == "awaiting_approval"),
        "completed_requests": sum(1 for r in reqs if r.status in ("fulfilled", "closed")),
        "active_workflows": sum(1 for r in reqs if r.status in ("processing", "inviting_donors", "partially_fulfilled")),
        "invitations_total": sum(inv.values()),
        "invitations_pending": inv.get("pending", 0),
        "invitations_accepted": inv.get("accepted", 0),
        "invitations_declined": inv.get("declined", 0),
        "invitations_expired": inv.get("expired", 0),
        "agent_runs_failed": db.scalar(
            select(func.count()).select_from(AgentRun).where(AgentRun.status == "failed")
        ) or 0,
    }


def blood_group_demand(db: Session, hospital_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    req_q = select(BloodRequest.blood_group, func.count(), func.sum(BloodRequest.units_requested)).group_by(
        BloodRequest.blood_group
    )
    open_q = req_q.where(BloodRequest.status.in_(OPEN_STATUSES))
    if hospital_id:
        req_q = req_q.where(BloodRequest.hospital_id == hospital_id)
        open_q = open_q.where(BloodRequest.hospital_id == hospital_id)
    totals = {g: (c, u) for g, c, u in db.execute(req_q).all()}
    opens = {g: (c, u) for g, c, u in db.execute(open_q).all()}
    donors = dict(db.execute(select(Donor.blood_group, func.count()).group_by(Donor.blood_group)).all())
    avail = dict(
        db.execute(
            select(Donor.blood_group, func.count()).where(Donor.availability == "available").group_by(Donor.blood_group)
        ).all()
    )
    return [
        {
            "blood_group": g,
            "requests": totals.get(g, (0, 0))[0],
            "units_requested": int(totals.get(g, (0, 0))[1] or 0),
            "open_requests": opens.get(g, (0, 0))[0],
            "open_units": int(opens.get(g, (0, 0))[1] or 0),
            "registered_donors": donors.get(g, 0),
            "available_donors": avail.get(g, 0),
        }
        for g in BLOOD_GROUPS
    ]


def invitation_stats(db: Session, hospital_id: uuid.UUID | None = None) -> dict[str, Any]:
    q = select(Invitation)
    if hospital_id:
        q = q.join(BloodRequest, Invitation.request_id == BloodRequest.id).where(BloodRequest.hospital_id == hospital_id)
    invs = db.scalars(q).all()
    responded = [i for i in invs if i.status in ("accepted", "declined")]
    accepted = sum(1 for i in invs if i.status == "accepted")
    times = [
        (i.responded_at - i.sent_at).total_seconds() / 60
        for i in responded if i.responded_at and i.sent_at
    ]
    return {
        "demo_data": True,
        "total": len(invs),
        "by_status": {s: sum(1 for i in invs if i.status == s) for s in ("pending", "accepted", "declined", "expired")},
        "acceptance_rate": round(accepted / len(responded), 3) if responded else None,
        "avg_response_minutes": round(sum(times) / len(times), 1) if times else None,
    }


def request_context(db: Session, req: BloodRequest) -> dict[str, Any]:
    """Small snapshot logged at the end of a workflow run."""
    open_same = db.scalar(
        select(func.count()).select_from(BloodRequest).where(
            BloodRequest.blood_group == req.blood_group, BloodRequest.status.in_(OPEN_STATUSES)
        )
    ) or 0
    avail_same = db.scalar(
        select(func.count()).select_from(Donor).where(
            Donor.blood_group == req.blood_group, Donor.availability == "available"
        )
    ) or 0
    return {"open_requests_same_group": open_same, "available_donors_same_group": avail_same}
