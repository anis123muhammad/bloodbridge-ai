import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.orchestrator import WorkflowConflict, handle_response
from app.api.common import Pagination, donor_of, hospital_of, invitation_out
from app.core.deps import get_current_user, require_roles
from app.core.responses import ok, paginated
from app.db.session import get_db
from app.models import BloodRequest, Invitation, User
from app.schemas import RespondIn

router = APIRouter(prefix="/invitations", tags=["Invitations"])


def _scoped(db: Session, user: User):
    q = select(Invitation)
    if user.role == "donor":
        donor = donor_of(db, user)
        q = q.where(Invitation.donor_id == (donor.id if donor else None))
    elif user.role == "hospital":
        hospital = hospital_of(db, user)
        q = q.join(BloodRequest, Invitation.request_id == BloodRequest.id).where(
            BloodRequest.hospital_id == (hospital.id if hospital else None))
    return q


def _get_visible(db: Session, invitation_id: uuid.UUID, user: User) -> Invitation:
    inv = db.scalar(_scoped(db, user).where(Invitation.id == invitation_id))
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    return inv


@router.get("")
def list_invitations(
    page: Pagination = Depends(),
    status_: str | None = Query(None, alias="status"),
    request_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _scoped(db, user)
    if status_:
        q = q.where(Invitation.status.in_(status_.split(",")))
    if request_id:
        q = q.where(Invitation.request_id == request_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(Invitation.sent_at.desc()).offset(page.offset).limit(page.page_size)).all()
    return paginated([invitation_out(i) for i in items], total, page.page, page.page_size)


@router.get("/{invitation_id}")
def get_invitation(invitation_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(invitation_out(_get_visible(db, invitation_id, user)))


@router.post("/{invitation_id}/respond")
def respond(invitation_id: uuid.UUID, body: RespondIn, user: User = Depends(require_roles("donor")),
            db: Session = Depends(get_db)):
    inv = _get_visible(db, invitation_id, user)  # donors only ever see their own invitations
    try:
        result = handle_response(db, inv, body.response, body.message, user.id)
    except WorkflowConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    db.refresh(inv)
    return ok({"invitation": invitation_out(inv), **result}, f"Invitation {body.response}")
