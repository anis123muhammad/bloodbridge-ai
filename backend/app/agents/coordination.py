"""Coordination Agent: turns HUMAN-APPROVED matches into simulated in-app invitations.

No real SMS, calls or emails are ever sent. Invitations are only created for
matches a hospital user or admin explicitly approved, and the unique constraint
(request_id, donor_id) plus an explicit check prevents duplicates on retry.
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BloodRequest, DonorMatch, Invitation
from app.services.audit import log_event


def create_invitations(db: Session, req: BloodRequest, approved: list[DonorMatch]) -> dict[str, Any]:
    already = set(db.scalars(select(Invitation.donor_id).where(Invitation.request_id == req.id)))
    created, skipped = [], []
    for match in approved:
        if match.status != "approved":
            continue  # approval gate: never invite without approval
        if match.donor_id in already:
            skipped.append(str(match.donor_id))
            continue
        inv = Invitation(request_id=req.id, donor_id=match.donor_id, match_id=match.id, status="pending")
        db.add(inv)
        db.flush()
        already.add(match.donor_id)
        created.append(inv)
        log_event(
            db, action="invitation.created", entity_type="invitation", entity_id=inv.id,
            actor_type="agent", actor_id="coordination", request_id=req.id,
            meta={"donor_id": str(match.donor_id), "simulated": True},
        )
    return {"created": created, "skipped_duplicates": skipped}
