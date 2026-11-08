import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.agents import request_analysis
from app.agents.base import AGENT_DISPLAY_NAMES, agent_step
from app.agents.orchestrator import WorkflowConflict, WorkflowFailed, approve_matches, run_workflow
from app.agents.priority_manager import LEVEL_RANK
from app.api.common import Pagination, get_request_for_user, hospital_of, match_out, request_detail_out, request_out
from app.core.deps import require_roles
from app.core.responses import ok, paginated
from app.db.session import get_db
from app.models import AgentRun, AuditLog, BloodRequest, DonorMatch, Invitation, User
from app.schemas import AnalyzeTextIn, ApproveMatchesIn, RequestCreateIn, RequestUpdateIn, TimelineEvent
from app.services.audit import log_event
from app.utils.time import as_aware, utcnow

router = APIRouter(prefix="/requests", tags=["Requests"])

staff = require_roles("hospital", "admin")
EDITABLE_STATUSES = ("draft", "submitted", "awaiting_approval")


def _conflict(exc: Exception):
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/analyze-text")
def analyze_text(body: AnalyzeTextIn, user: User = Depends(staff), db: Session = Depends(get_db)):
    """Request Analysis Agent on free text. Returns structured fields to pre-fill the form; saves no request."""
    hospital = hospital_of(db, user)
    with agent_step(db, "request_analysis", None, f"Free text: {body.text[:300]}") as run:
        result = request_analysis.analyze_text(body.text, default_location=hospital.city if hospital else None)
        run.output_data = {**result, "fields": {k: str(v) for k, v in result["fields"].items()}}
        run.output_summary = (f"Extracted {len(result['fields'])} field(s) via {result['source']}; "
                              f"missing: {', '.join(result['missing_fields']) or 'none'}.")
    db.commit()
    return ok(result, "Text analyzed")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_request(body: RequestCreateIn, user: User = Depends(require_roles("hospital")),
                   db: Session = Depends(get_db)):
    hospital = hospital_of(db, user)
    if hospital is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hospital profile not found")
    if as_aware(body.deadline) <= utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Deadline must be in the future")
    req = BloodRequest(
        hospital_id=hospital.id, title=body.title, blood_group=body.blood_group,
        units_requested=body.units_requested, urgency=body.urgency,
        location=(body.location or hospital.city).strip(), deadline=body.deadline,
        description=body.description, contact_info=body.contact_info, status="submitted",
    )
    db.add(req)
    db.flush()
    log_event(db, action="request.created", entity_type="blood_request", entity_id=req.id,
              actor_type="user", actor_id=user.id, request_id=req.id,
              meta={"blood_group": req.blood_group, "units": req.units_requested, "urgency": req.urgency})
    db.commit()
    message = "Request created successfully"
    if body.auto_run_workflow:
        try:
            run_workflow(db, req, user.id)
            message += "; workflow completed"
        except (WorkflowConflict, WorkflowFailed) as exc:
            message += f"; workflow did not complete: {exc}"
        db.refresh(req)
    return ok(request_detail_out(req), message)


@router.get("")
def list_requests(
    page: Pagination = Depends(),
    status_: str | None = Query(None, alias="status"),
    urgency: str | None = None,
    priority: str | None = None,
    blood_group: str | None = None,
    search: str | None = None,
    sort: str = Query("created", pattern="^(created|priority|deadline)$"),
    user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    q = select(BloodRequest)
    if user.role == "hospital":
        hospital = hospital_of(db, user)
        q = q.where(BloodRequest.hospital_id == (hospital.id if hospital else None))
    if status_:
        q = q.where(BloodRequest.status.in_(status_.split(",")))
    if urgency:
        q = q.where(BloodRequest.urgency == urgency)
    if priority:
        q = q.where(BloodRequest.priority == priority)
    if blood_group:
        q = q.where(BloodRequest.blood_group == blood_group.upper().replace(" ", "+"))
    if search:
        like = f"%{search}%"
        q = q.where(or_(BloodRequest.title.ilike(like), BloodRequest.location.ilike(like),
                        BloodRequest.description.ilike(like)))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    if sort == "priority":  # the operational queue: priority level, then nearest deadline
        rank = case(LEVEL_RANK, value=BloodRequest.priority, else_=len(LEVEL_RANK))
        q = q.order_by(rank, BloodRequest.deadline.asc())
    elif sort == "deadline":
        q = q.order_by(BloodRequest.deadline.asc())
    else:
        q = q.order_by(BloodRequest.created_at.desc())
    items = db.scalars(q.offset(page.offset).limit(page.page_size)).all()
    return paginated([request_out(r) for r in items], total, page.page, page.page_size)


@router.get("/{request_id}")
def get_request(request_id: uuid.UUID, user: User = Depends(staff), db: Session = Depends(get_db)):
    return ok(request_detail_out(get_request_for_user(db, request_id, user)))


@router.patch("/{request_id}")
def update_request(request_id: uuid.UUID, body: RequestUpdateIn, user: User = Depends(staff),
                   db: Session = Depends(get_db)):
    req = get_request_for_user(db, request_id, user)
    changes = body.model_dump(exclude_unset=True)
    new_status = changes.pop("status", None)
    if changes:
        if req.status not in EDITABLE_STATUSES:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"Request details cannot be edited while '{req.status}'.")
        if "deadline" in changes and as_aware(changes["deadline"]) <= utcnow():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Deadline must be in the future")
        for k, v in changes.items():
            setattr(req, k, v)
        # Edited details invalidate earlier analysis; staff re-runs the workflow.
        if req.status != "draft":
            req.status = "submitted"
        req.status_note = "Details edited. Run the workflow again to refresh priority and matches."
        db.query(DonorMatch).filter(DonorMatch.request_id == req.id, DonorMatch.status == "suggested").delete()
        log_event(db, action="request.updated", entity_type="blood_request", entity_id=req.id,
                  actor_type="user", actor_id=user.id, request_id=req.id,
                  meta={"fields": list(changes.keys())})
    if new_status:
        if req.status in ("closed", "cancelled"):
            raise HTTPException(status.HTTP_409_CONFLICT, f"Request is already {req.status}.")
        old = req.status
        req.status = new_status
        req.status_note = {
            "fulfilled": "Marked fulfilled by hospital staff.",
            "closed": "Closed by hospital staff.",
            "cancelled": "Cancelled by hospital staff.",
        }[new_status]
        log_event(db, action="request.status_updated", entity_type="blood_request", entity_id=req.id,
                  actor_type="user", actor_id=user.id, request_id=req.id,
                  meta={"from": old, "to": new_status, "manual": True})
    db.commit()
    db.refresh(req)
    return ok(request_detail_out(req), "Request updated")


@router.post("/{request_id}/run-workflow")
def run_request_workflow(request_id: uuid.UUID, user: User = Depends(staff), db: Session = Depends(get_db)):
    req = get_request_for_user(db, request_id, user)
    try:
        result = run_workflow(db, req, user.id)
    except WorkflowConflict as exc:
        raise _conflict(exc)
    except WorkflowFailed as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    db.refresh(req)
    return ok({"request": request_detail_out(req), "workflow": result}, "Workflow completed")


@router.get("/{request_id}/matches")
def list_matches(request_id: uuid.UUID, status_: str | None = Query(None, alias="status"),
                 user: User = Depends(staff), db: Session = Depends(get_db)):
    req = get_request_for_user(db, request_id, user)
    q = select(DonorMatch).where(DonorMatch.request_id == req.id)
    if status_:
        q = q.where(DonorMatch.status.in_(status_.split(",")))
    matches = db.scalars(q.order_by(DonorMatch.match_score.desc())).all()
    inv_status = dict(db.execute(
        select(Invitation.donor_id, Invitation.status).where(Invitation.request_id == req.id)).all())
    return ok({
        "items": [match_out(m, inv_status.get(m.donor_id)) for m in matches],
        "disclaimer": "Match score is an operational ranking of synthetic records, not medical "
                      "compatibility or eligibility. Staff must verify suitability.",
    })


@router.post("/{request_id}/approve-matches")
def approve_request_matches(request_id: uuid.UUID, body: ApproveMatchesIn, user: User = Depends(staff),
                            db: Session = Depends(get_db)):
    if not body.approve_ids and not body.reject_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide approve_ids and/or reject_ids")
    req = get_request_for_user(db, request_id, user)
    try:
        result = approve_matches(db, req, body.approve_ids, body.reject_ids, user.id)
    except WorkflowConflict as exc:
        raise _conflict(exc)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except WorkflowFailed as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    db.refresh(req)
    return ok({"request": request_detail_out(req), **result},
              f"{result['invitations_created']} simulated invitation(s) created")


@router.get("/{request_id}/timeline")
def request_timeline(request_id: uuid.UUID, user: User = Depends(staff), db: Session = Depends(get_db)):
    req = get_request_for_user(db, request_id, user)
    runs = db.scalars(select(AgentRun).where(AgentRun.request_id == req.id)).all()
    logs = db.scalars(select(AuditLog).where(AuditLog.request_id == req.id)).all()
    events = [
        TimelineEvent(kind="agent_run", id=r.id, at=as_aware(r.started_at),
                      title=AGENT_DISPLAY_NAMES.get(r.agent_name, r.agent_name), status=r.status,
                      summary=r.output_summary or r.error_message,
                      details={"agent_name": r.agent_name, "input": r.input_summary, "output": r.output_data,
                               "error": r.error_message,
                               "completed_at": as_aware(r.completed_at).isoformat() if r.completed_at else None})
        for r in runs
    ] + [
        TimelineEvent(kind="audit", id=a.id, at=as_aware(a.created_at), title=a.action,
                      summary=f"{a.actor_type}:{a.actor_id}", details=a.meta)
        for a in logs
    ]
    events.sort(key=lambda e: e.at)
    return ok([e.model_dump() for e in events])
