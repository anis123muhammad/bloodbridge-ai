"""Agent failure cases: a crashing agent is recorded, leaves nothing half-done and is safe to retry."""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.agents import coordination, donor_matching
from app.db.session import SessionLocal
from app.models import AgentRun, AuditLog, DonorMatch, Invitation
from app.utils.time import utcnow
from tests.conftest import login


def _boom(*args, **kwargs):
    raise RuntimeError("simulated agent crash")


def _create_request(client, headers, title: str) -> str:
    r = client.post("/api/requests", headers=headers, json={
        "title": title, "blood_group": "O+", "units_requested": 2, "urgency": "urgent",
        "location": "Faisalabad", "deadline": (utcnow() + timedelta(hours=4)).isoformat()})
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def _count(model, rid: str) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(model.request_id == uuid.UUID(rid)))


def _supervisor_failures(rid: str) -> list[AgentRun]:
    with SessionLocal() as db:
        return list(db.scalars(select(AgentRun).where(
            AgentRun.request_id == uuid.UUID(rid), AgentRun.agent_name == "supervisor",
            AgentRun.status == "failed")))


def _audit_actions(rid: str) -> list[str]:
    with SessionLocal() as db:
        return list(db.scalars(select(AuditLog.action).where(AuditLog.request_id == uuid.UUID(rid))))


def test_matching_failure_is_recorded_and_retry_succeeds(client, monkeypatch):
    hosp = login(client, "hospital@bloodbridge.demo")
    rid = _create_request(client, hosp, "FAIL-MATCH-001")

    # 1. Donor Matching crashes mid-workflow
    monkeypatch.setattr(donor_matching, "find_matching_donors", _boom)
    r = client.post(f"/api/requests/{rid}/run-workflow", headers=hosp)
    assert r.status_code == 500
    assert r.json()["success"] is False and "donor_matching failed" in r.json()["message"]

    # Request is back to a runnable state with an explanation, nothing half-saved
    req = client.get(f"/api/requests/{rid}", headers=hosp).json()["data"]
    assert req["status"] == "submitted"
    assert "safe to retry" in req["status_note"]
    assert _count(DonorMatch, rid) == 0 and _count(Invitation, rid) == 0

    # Supervisor recorded the failure; audit trail shows it
    failures = _supervisor_failures(rid)
    assert len(failures) == 1 and "simulated agent crash" in failures[0].error_message
    assert "workflow.failed" in _audit_actions(rid)

    # 2. Agent recovers: the retry completes without duplicating anything
    monkeypatch.undo()
    r = client.post(f"/api/requests/{rid}/run-workflow", headers=hosp)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["request"]["status"] == "awaiting_approval"
    matches = _count(DonorMatch, rid)
    assert matches > 0 and _count(Invitation, rid) == 0  # still waiting for human approval
    with SessionLocal() as db:
        donor_ids = list(db.scalars(select(DonorMatch.donor_id).where(DonorMatch.request_id == uuid.UUID(rid))))
    assert len(donor_ids) == len(set(donor_ids))


def test_coordination_failure_sends_nothing_and_reapproval_succeeds(client, monkeypatch):
    # hospital2 so this test's invitations don't change hospital@'s analytics in test_full_workflow
    hosp = login(client, "hospital2@bloodbridge.demo")
    rid = _create_request(client, hosp, "FAIL-COORD-001")
    assert client.post(f"/api/requests/{rid}/run-workflow", headers=hosp).status_code == 200
    items = client.get(f"/api/requests/{rid}/matches", headers=hosp).json()["data"]
    items = items["items"] if isinstance(items, dict) else items
    approve = [m["id"] for m in items[:2]]

    # 1. Coordination crashes after the human approved
    monkeypatch.setattr(coordination, "create_invitations", _boom)
    r = client.post(f"/api/requests/{rid}/approve-matches", headers=hosp,
                    json={"approve_ids": approve, "reject_ids": []})
    assert r.status_code == 500 and r.json()["success"] is False
    assert _count(Invitation, rid) == 0  # no invitation was sent
    req = client.get(f"/api/requests/{rid}", headers=hosp).json()["data"]
    assert req["status"] == "awaiting_approval" and "safe to retry" in req["status_note"]
    assert len(_supervisor_failures(rid)) == 1

    # 2. Re-approving after recovery creates exactly one invitation per approved donor
    monkeypatch.undo()
    r = client.post(f"/api/requests/{rid}/approve-matches", headers=hosp,
                    json={"approve_ids": approve, "reject_ids": []})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["invitations_created"] == len(approve)
    assert _count(Invitation, rid) == len(approve)

    # Cancel so the invited demo donors are not "busy" for other tests' requests
    r = client.patch(f"/api/requests/{rid}", headers=hosp, json={"status": "cancelled"})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("agent", ["request_analysis", "priority_manager"])
def test_early_agent_failure_leaves_request_retryable(client, monkeypatch, agent):
    from app.agents import priority_manager, request_analysis

    target = {"request_analysis": (request_analysis, "analyze_request"),
              "priority_manager": (priority_manager, "calculate_priority")}[agent]
    hosp = login(client, "hospital@bloodbridge.demo")
    rid = _create_request(client, hosp, f"FAIL-{agent.upper()}")

    monkeypatch.setattr(*target, _boom)
    r = client.post(f"/api/requests/{rid}/run-workflow", headers=hosp)
    assert r.status_code == 500 and f"{agent} failed" in r.json()["message"]
    req = client.get(f"/api/requests/{rid}", headers=hosp).json()["data"]
    assert req["status"] == "submitted" and req["priority"] in (None, "")  # nothing half-applied
    assert len(_supervisor_failures(rid)) == 1

    monkeypatch.undo()
    assert client.post(f"/api/requests/{rid}/run-workflow", headers=hosp).status_code == 200
