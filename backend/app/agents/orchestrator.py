"""Workflow orchestrator (supervisor layer).

A simple, explicit state machine that calls each agent in order, records every
step as an AgentRun plus audit events, enforces the human-approval gate, and
recovers safely from failures (a retry never duplicates matches or invitations).

    submitted --run_workflow--> processing --> awaiting_approval
    awaiting_approval --approve_matches (HUMAN)--> inviting_donors
    inviting_donors --donor responses / timeouts--> partially_fulfilled | fulfilled
                     +--> awaiting_approval (alternatives suggested, need approval again)
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import analytics_agent, coordination, donor_matching, follow_up, priority_manager, request_analysis
from app.agents.base import agent_step
from app.core.config import get_settings
from app.models import AgentRun, BloodRequest, DonorMatch, Invitation
from app.services.audit import log_event
from app.utils.time import as_aware, utcnow

TERMINAL = ("fulfilled", "closed", "cancelled")
RUNNABLE = ("draft", "submitted", "awaiting_approval")
APPROVABLE = ("awaiting_approval", "inviting_donors", "partially_fulfilled")


class WorkflowConflict(Exception):
    """The request is not in a state that allows this action (maps to HTTP 409)."""


class WorkflowFailed(Exception):
    """An agent failed; the failure is recorded and the workflow can be retried."""


def _fail_safely(db: Session, request_id: uuid.UUID, prev_status: str, stage: str, exc: Exception) -> None:
    db.rollback()
    req = db.get(BloodRequest, request_id)
    req.status = prev_status if prev_status not in ("processing",) else "submitted"
    req.status_note = f"{stage} failed: {exc}. Nothing was sent; it is safe to retry."
    db.add(AgentRun(
        request_id=request_id, agent_name="supervisor", status="failed",
        input_summary=f"stage={stage}", error_message=str(exc)[:1000],
        started_at=utcnow(), completed_at=utcnow(),
    ))
    log_event(db, action="workflow.failed", entity_type="blood_request", entity_id=request_id,
              actor_type="agent", actor_id="supervisor", request_id=request_id,
              meta={"stage": stage, "error": str(exc)[:300]})
    db.commit()


# ---------------------------------------------------------------- run workflow
def run_workflow(db: Session, req: BloodRequest, actor_id: uuid.UUID) -> dict[str, Any]:
    if req.status not in RUNNABLE:
        raise WorkflowConflict(f"Workflow cannot run while the request is '{req.status}'.")
    prev_status, rid = req.status, req.id
    req.status = "processing"
    log_event(db, action="workflow.started", entity_type="blood_request", entity_id=rid,
              actor_type="user", actor_id=actor_id, request_id=rid)
    db.flush()
    stage = "request_analysis"
    try:
        # 1. Request Analysis
        with agent_step(db, "request_analysis", rid,
                        f"{req.units_requested} x {req.blood_group}, urgency={req.urgency}, "
                        f"location={req.location}, deadline={as_aware(req.deadline).isoformat()}") as run:
            analysis = request_analysis.analyze_request(req)
            run.output_data = analysis
            if analysis["validation_status"] != "valid":
                run.output_summary = "Validation failed: " + " ".join(analysis["errors"])
            else:
                run.output_summary = "Request is valid." + (
                    " Warnings: " + " ".join(analysis["warnings"]) if analysis["warnings"] else "")
        log_event(db, action="request.validated", entity_type="blood_request", entity_id=rid,
                  actor_type="agent", actor_id="request_analysis", request_id=rid,
                  meta={"validation_status": analysis["validation_status"], "errors": analysis["errors"],
                        "warnings": analysis["warnings"]})
        if analysis["validation_status"] != "valid":
            req.status = "draft"
            req.status_note = "Needs correction: " + " ".join(analysis["errors"])
            db.commit()
            return {"status": req.status, "analysis": analysis}
        req.blood_group = analysis["normalized"].get("blood_group", req.blood_group)

        # 2. Priority Manager
        stage = "priority_manager"
        with agent_step(db, "priority_manager", rid, f"urgency={req.urgency}, units={req.units_requested}") as run:
            prio = priority_manager.calculate_priority(req)
            req.priority, req.priority_score, req.priority_reason = prio["priority"], prio["score"], prio["reason"]
            run.output_data, run.output_summary = prio, prio["reason"]
        log_event(db, action="priority.assigned", entity_type="blood_request", entity_id=rid,
                  actor_type="agent", actor_id="priority_manager", request_id=rid,
                  meta={"priority": prio["priority"], "score": prio["score"]})

        # 3. Donor Matching (skip donors already invited for this request)
        stage = "donor_matching"
        invited = set(db.scalars(select(Invitation.donor_id).where(Invitation.request_id == rid)))
        with agent_step(db, "donor_matching", rid,
                        f"group={req.blood_group}, location={req.location}") as run:
            result = donor_matching.find_matching_donors(db, req, exclude_donor_ids=invited)
            new = donor_matching.save_matches(db, req, result["candidates"])
            run.output_data = {k: v for k, v in result.items() if k != "candidates"} | {
                "candidates": [{**c, "donor_id": str(c["donor_id"])} for c in result["candidates"]],
                "new_matches_saved": len(new),
            }
            run.output_summary = (
                f"{len(result['candidates'])} candidate(s) within {result['radius_km']:.0f} km "
                f"(groups considered: {', '.join(result['groups_considered'])}; "
                f"{result['pool_size']} donors passed SQL filters)."
            )
        log_event(db, action="matching.completed", entity_type="blood_request", entity_id=rid,
                  actor_type="agent", actor_id="donor_matching", request_id=rid,
                  meta={"candidates": len(result["candidates"]), "radius_km": result["radius_km"]})

        # 4. Analytics snapshot
        stage = "analytics"
        with agent_step(db, "analytics", rid, f"context for {req.blood_group}") as run:
            ctx = analytics_agent.request_context(db, req)
            run.output_data = ctx
            run.output_summary = (f"{ctx['open_requests_same_group']} open {req.blood_group} request(s); "
                                  f"{ctx['available_donors_same_group']} available {req.blood_group} donor(s) (demo data).")

        # 5. Human approval gate
        suggested = db.scalar(select(DonorMatch.id).where(DonorMatch.request_id == rid,
                                                          DonorMatch.status == "suggested").limit(1))
        if suggested:
            req.status = "awaiting_approval"
            req.status_note = (f"{len(result['candidates'])} candidate(s) ready. Waiting for hospital staff "
                               "to approve before any invitation is created.")
            log_event(db, action="approval.requested", entity_type="blood_request", entity_id=rid,
                      actor_type="agent", actor_id="supervisor", request_id=rid)
        else:
            req.status = "submitted"
            req.status_note = (f"No eligible candidates found within {get_settings().radius_steps[-1]:.0f} km. "
                               "Escalated to admin: consider blood bank stock or manual outreach.")
            log_event(db, action="workflow.escalated", entity_type="blood_request", entity_id=rid,
                      actor_type="agent", actor_id="supervisor", request_id=rid, meta={"reason": "no_candidates"})
        db.commit()
        return {"status": req.status, "analysis": analysis, "priority": prio,
                "candidates_found": len(result["candidates"]), "radius_km": result["radius_km"]}
    except Exception as exc:
        _fail_safely(db, rid, prev_status, stage, exc)
        raise WorkflowFailed(f"{stage} failed: {exc}") from exc


# ---------------------------------------------------------------- human approval
def approve_matches(db: Session, req: BloodRequest, approve_ids: list[uuid.UUID],
                    reject_ids: list[uuid.UUID], actor_id: uuid.UUID) -> dict[str, Any]:
    if req.status not in APPROVABLE:
        raise WorkflowConflict(f"Matches cannot be approved while the request is '{req.status}'.")
    prev_status = req.status
    overlap = set(approve_ids) & set(reject_ids)
    if overlap:
        raise ValueError("A match cannot be both approved and rejected.")
    matches = {m.id: m for m in db.scalars(select(DonorMatch).where(DonorMatch.request_id == req.id))}
    unknown = [str(i) for i in [*approve_ids, *reject_ids] if i not in matches]
    if unknown:
        raise ValueError(f"Match id(s) not found for this request: {', '.join(unknown)}")

    for mid in approve_ids:
        if matches[mid].status == "suggested":
            matches[mid].status = "approved"
            log_event(db, action="match.approved", entity_type="donor_match", entity_id=mid,
                      actor_type="user", actor_id=actor_id, request_id=req.id)
    for mid in reject_ids:
        if matches[mid].status == "suggested":
            matches[mid].status = "rejected"
            log_event(db, action="match.rejected", entity_type="donor_match", entity_id=mid,
                      actor_type="user", actor_id=actor_id, request_id=req.id)
    log_event(db, action="approval.granted", entity_type="blood_request", entity_id=req.id,
              actor_type="user", actor_id=actor_id, request_id=req.id,
              meta={"approved": len(approve_ids), "rejected": len(reject_ids)})
    db.flush()

    try:
        # Every approved match without an invitation (so a retry after failure catches up)
        approved = [m for m in matches.values() if m.status == "approved"]
        with agent_step(db, "coordination", req.id, f"{len(approved)} approved match(es)") as run:
            res = coordination.create_invitations(db, req, approved)
            run.output_data = {"created": [str(i.id) for i in res["created"]],
                               "skipped_duplicates": res["skipped_duplicates"], "simulated": True}
            run.output_summary = (f"Created {len(res['created'])} simulated in-app invitation(s); "
                                  f"skipped {len(res['skipped_duplicates'])} duplicate(s). No real messages sent.")
        if res["created"]:
            req.status = "inviting_donors"
        _apply_follow_up(db, req, trigger="approval")
        db.commit()
    except Exception as exc:
        _fail_safely(db, req.id, prev_status, "coordination", exc)
        raise WorkflowFailed(f"coordination failed: {exc}") from exc
    return {"status": req.status, "invitations_created": len(res["created"])}


# ---------------------------------------------------------------- donor response
def handle_response(db: Session, inv: Invitation, response: str, message: str | None,
                    actor_id: uuid.UUID) -> dict[str, Any]:
    if inv.status != "pending":
        raise WorkflowConflict(f"This invitation is already '{inv.status}'.")
    req = inv.request
    if req.status in ("closed", "cancelled"):
        raise WorkflowConflict(f"The request is {req.status}; responses are no longer accepted.")

    if message and message.strip():
        with agent_step(db, "follow_up", req.id, f"Donor reply ({response}): {message[:200]}") as run:
            analysis = follow_up.analyze_donor_reply(message, req.deadline)
            run.output_data = analysis
            flags = []
            if analysis["conflicts_with_deadline"]:
                flags.append(f"available from {analysis['available_from']}, after the deadline")
            if analysis["concerns"]:
                flags.append("staff should review: " + ", ".join(analysis["concerns"]))
            run.output_summary = "Analyzed donor reply" + (" - " + "; ".join(flags) if flags else " - no issues flagged.")
        inv.response_message = message.strip()
        inv.response_analysis = analysis

    inv.status = response
    inv.responded_at = utcnow()
    log_event(db, action=f"invitation.{response}", entity_type="invitation", entity_id=inv.id,
              actor_type="user", actor_id=actor_id, request_id=req.id,
              meta={"needs_staff_review": (inv.response_analysis or {}).get("needs_staff_review", False)})
    db.flush()
    _apply_follow_up(db, req, trigger=f"donor {response}")
    db.commit()
    return {"invitation_status": inv.status, "request_status": req.status}


# ---------------------------------------------------------------- follow-up
def _apply_follow_up(db: Session, req: BloodRequest, trigger: str) -> None:
    if req.status in TERMINAL:
        return
    db.flush()
    db.expire(req, ["invitations", "matches"])
    old_status = req.status
    with agent_step(db, "follow_up", req.id, f"trigger={trigger}") as run:
        counts = follow_up.response_counts(req)
        status, note, need_alt = follow_up.decide_next_status(req, counts)
        alternatives = 0
        if need_alt and status != "fulfilled":
            contacted = set(db.scalars(select(DonorMatch.donor_id).where(DonorMatch.request_id == req.id)))
            contacted |= set(db.scalars(select(Invitation.donor_id).where(Invitation.request_id == req.id)))
            want = max(counts["still_needed"] * 2 - counts["pending"], 1)
            result = donor_matching.find_matching_donors(db, req, exclude_donor_ids=contacted, limit=want)
            new = donor_matching.save_matches(db, req, result["candidates"])
            alternatives = len(new)
            if new:
                status = "awaiting_approval"
                note += f" Follow-up suggested {len(new)} alternative donor(s); waiting for staff approval."
                log_event(db, action="followup.alternatives_suggested", entity_type="blood_request",
                          entity_id=req.id, actor_type="agent", actor_id="follow_up", request_id=req.id,
                          meta={"count": len(new), "radius_km": result["radius_km"]})
            else:
                if counts["suggested_awaiting_approval"]:
                    status = "awaiting_approval"
                    note += f" {counts['suggested_awaiting_approval']} earlier suggestion(s) still awaiting approval."
                note += (f" No further new candidates within {result['radius_km']:.0f} km. "
                         "Escalated to admin: consider blood bank stock or manual outreach.")
                log_event(db, action="workflow.escalated", entity_type="blood_request", entity_id=req.id,
                          actor_type="agent", actor_id="follow_up", request_id=req.id,
                          meta={"reason": "no_alternatives"})
        req.status, req.status_note = status, note
        run.output_data = {**counts, "alternatives_suggested": alternatives, "new_status": status}
        run.output_summary = note
    if status != old_status:
        log_event(db, action="request.status_updated", entity_type="blood_request", entity_id=req.id,
                  actor_type="agent", actor_id="follow_up", request_id=req.id,
                  meta={"from": old_status, "to": status, "trigger": trigger})


def expire_stale_invitations(db: Session) -> int:
    """Mark pending invitations past the timeout as expired and follow up on their requests."""
    cutoff = follow_up.stale_invitation_cutoff()
    pending = db.scalars(select(Invitation).where(Invitation.status == "pending")).all()
    stale = [i for i in pending if as_aware(i.sent_at) < cutoff]
    touched: dict[uuid.UUID, BloodRequest] = {}
    for inv in stale:
        inv.status = "expired"
        inv.responded_at = utcnow()
        log_event(db, action="invitation.expired", entity_type="invitation", entity_id=inv.id,
                  actor_type="agent", actor_id="follow_up", request_id=inv.request_id)
        touched[inv.request_id] = inv.request
    for req in touched.values():
        _apply_follow_up(db, req, trigger="invitation timeout")
    db.commit()
    return len(stale)
