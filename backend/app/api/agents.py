import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.base import AGENT_DISPLAY_NAMES
from app.agents.orchestrator import expire_stale_invitations
from app.api.common import Pagination, hospital_of
from app.core.deps import require_roles
from app.core.responses import ok, paginated
from app.db.session import get_db
from app.models import AgentRun, AuditLog, BloodRequest, User
from app.schemas import AgentRunOut

router = APIRouter(prefix="/agents", tags=["Agents"])
staff = require_roles("hospital", "admin")


def _run_out(r: AgentRun) -> dict:
    return {**AgentRunOut.model_validate(r).model_dump(),
            "agent_display_name": AGENT_DISPLAY_NAMES.get(r.agent_name, r.agent_name)}


def _scope_runs(db: Session, user: User):
    q = select(AgentRun)
    if user.role == "hospital":
        hospital = hospital_of(db, user)
        q = q.join(BloodRequest, AgentRun.request_id == BloodRequest.id).where(
            BloodRequest.hospital_id == (hospital.id if hospital else None))
    return q


@router.get("/runs")
def list_runs(
    page: Pagination = Depends(),
    request_id: uuid.UUID | None = None,
    agent_name: str | None = None,
    status_: str | None = Query(None, alias="status"),
    user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    q = _scope_runs(db, user)
    if request_id:
        q = q.where(AgentRun.request_id == request_id)
    if agent_name:
        q = q.where(AgentRun.agent_name == agent_name)
    if status_:
        q = q.where(AgentRun.status == status_)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(AgentRun.started_at.desc()).offset(page.offset).limit(page.page_size)).all()
    return paginated([_run_out(r) for r in items], total, page.page, page.page_size)


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, user: User = Depends(staff), db: Session = Depends(get_db)):
    run = db.scalar(_scope_runs(db, user).where(AgentRun.id == run_id))
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")
    return ok(_run_out(run))


@router.get("/audit-logs")
def list_audit_logs(
    page: Pagination = Depends(),
    request_id: uuid.UUID | None = None,
    action: str | None = None,
    actor_type: str | None = None,
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    q = select(AuditLog)
    if request_id:
        q = q.where(AuditLog.request_id == request_id)
    if action:
        q = q.where(AuditLog.action.ilike(f"{action}%"))
    if actor_type:
        q = q.where(AuditLog.actor_type == actor_type)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(AuditLog.created_at.desc()).offset(page.offset).limit(page.page_size)).all()
    return paginated([
        {"id": a.id, "actor_type": a.actor_type, "actor_id": a.actor_id, "action": a.action,
         "entity_type": a.entity_type, "entity_id": a.entity_id, "request_id": a.request_id,
         "metadata": a.meta, "created_at": a.created_at}
        for a in items
    ], total, page.page, page.page_size)


@router.post("/follow-up/run")
def run_follow_up_now(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    """Run the Follow-up Agent's timeout sweep immediately (also runs in the background)."""
    expired = expire_stale_invitations(db)
    return ok({"expired_invitations": expired}, "Follow-up sweep completed")
