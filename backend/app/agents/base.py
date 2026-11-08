"""Shared agent plumbing: every agent step is recorded as an AgentRun row."""
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.models import AgentRun
from app.utils.time import utcnow

AGENT_DISPLAY_NAMES = {
    "request_analysis": "Request Analysis Agent",
    "priority_manager": "Priority Manager",
    "donor_matching": "Donor Matching Agent",
    "coordination": "Coordination Agent",
    "follow_up": "Follow-up Agent",
    "analytics": "Analytics Agent",
    "supervisor": "Supervisor & Audit Layer",
}


@contextmanager
def agent_step(
    db: Session, agent_name: str, request_id: uuid.UUID | None, input_summary: str
) -> Iterator[AgentRun]:
    """Create a running AgentRun, mark it completed on success or failed on error.

    The caller fills run.output_summary / run.output_data inside the block.
    """
    run = AgentRun(
        request_id=request_id,
        agent_name=agent_name,
        status="running",
        input_summary=input_summary[:1000],
    )
    db.add(run)
    db.flush()
    try:
        yield run
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.completed_at = utcnow()
        raise
    else:
        if run.status == "running":
            run.status = "completed"
        run.completed_at = utcnow()
        db.flush()


class AgentError(Exception):
    """A handled agent failure with a human-readable reason."""
