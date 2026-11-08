"""End-to-end: request -> agents -> human approval -> donor responses -> follow-up -> analytics."""
import uuid
from datetime import timedelta

from app.db.session import SessionLocal
from app.models import Invitation
from app.utils.time import utcnow
from tests.conftest import login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["success"] is True


def test_register_login_and_roles(client):
    r = client.post("/api/auth/register", json={
        "name": "Test Donor", "email": "new.donor@example.com", "password": "secret123",
        "role": "donor", "city": "Faisalabad", "blood_group": "b neg"})
    assert r.status_code == 201, r.text
    me = r.json()["data"]["me"]
    assert me["donor"]["blood_group"] == "B-" and me["donor"]["latitude"] is not None

    dup = client.post("/api/auth/register", json={
        "name": "Test Donor", "email": "new.donor@example.com", "password": "secret123",
        "role": "donor", "city": "Faisalabad", "blood_group": "B-"})
    assert dup.status_code == 409 and dup.json()["success"] is False

    bad = client.post("/api/auth/login", json={"email": "new.donor@example.com", "password": "wrong"})
    assert bad.status_code == 401

    donor = login(client, "new.donor@example.com", "secret123")
    assert client.get("/api/requests", headers=donor).status_code == 403  # backend role check
    assert client.get("/api/donors", headers=donor).status_code == 403
    assert client.get("/api/requests").status_code == 401


def test_validation_error_shape(client):
    h = login(client, "hospital@bloodbridge.demo")
    r = client.post("/api/requests", headers=h, json={"blood_group": "Z+", "units_requested": 0,
                                                      "deadline": "2030-01-01T00:00:00Z"})
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False and {e["field"] for e in body["errors"]} >= {"blood_group", "units_requested"}


def test_analyze_text_endpoint(client):
    h = login(client, "hospital@bloodbridge.demo")
    r = client.post("/api/requests/analyze-text", headers=h,
                    json={"text": "Urgently need two units of O positive blood in Faisalabad by tonight"})
    assert r.status_code == 200, r.text
    f = r.json()["data"]["fields"]
    assert f["blood_group"] == "O+" and f["units_requested"] == 2 and f["urgency"] == "urgent"


def test_full_workflow(client):
    hosp = login(client, "hospital@bloodbridge.demo")
    admin = login(client, "admin@bloodbridge.demo")
    ahmed = login(client, "donor@bloodbridge.demo")

    # 1. Hospital creates a request
    deadline = (utcnow() + timedelta(hours=2)).isoformat()
    r = client.post("/api/requests", headers=hosp, json={
        "title": "TEST-001", "blood_group": "O+", "units_requested": 2, "urgency": "urgent",
        "location": "Faisalabad", "deadline": deadline,
        "description": "Accident patient, need 2 units O+ urgently"})
    assert r.status_code == 201, r.text
    rid = r.json()["data"]["id"]
    assert r.json()["data"]["status"] == "submitted"

    # Other hospitals cannot see it
    other = login(client, "hospital2@bloodbridge.demo")
    assert client.get(f"/api/requests/{rid}", headers=other).status_code == 404

    # 2. Agents: analysis -> priority -> matching -> awaiting human approval
    r = client.post(f"/api/requests/{rid}/run-workflow", headers=hosp)
    assert r.status_code == 200, r.text
    req = r.json()["data"]["request"]
    assert req["status"] == "awaiting_approval"
    assert req["priority"] in ("high", "critical") and "score" in req["priority_reason"]
    # running again while awaiting approval must not duplicate matches
    n1 = len(client.get(f"/api/requests/{rid}/matches", headers=hosp).json()["data"]["items"])
    client.post(f"/api/requests/{rid}/run-workflow", headers=hosp)
    matches = client.get(f"/api/requests/{rid}/matches", headers=hosp).json()["data"]["items"]
    assert len(matches) == n1 and len(matches) >= 2
    assert all(m["donor_blood_group"] in ("O+", "O-") for m in matches)
    assert matches[0]["match_reasons"] and matches == sorted(matches, key=lambda m: -m["match_score"])
    ahmed_match = next(m for m in matches if m["donor_name"].startswith("Ahmed Khan"))

    # No invitations exist before human approval
    assert client.get(f"/api/invitations?request_id={rid}", headers=hosp).json()["data"]["total"] == 0

    # 3. Human approval -> Coordination Agent creates simulated invitations
    other_match = next(m for m in matches if m["id"] != ahmed_match["id"])
    approve = [ahmed_match["id"], other_match["id"]]
    r = client.post(f"/api/requests/{rid}/approve-matches", headers=hosp, json={"approve_ids": approve})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["invitations_created"] == 2
    assert r.json()["data"]["request"]["status"] == "inviting_donors"
    # Re-approving never duplicates invitations
    r = client.post(f"/api/requests/{rid}/approve-matches", headers=hosp, json={"approve_ids": approve})
    assert r.json()["data"]["invitations_created"] == 0
    assert client.get(f"/api/invitations?request_id={rid}", headers=hosp).json()["data"]["total"] == 2

    # 4. Donor sees the invitation and accepts with a free-text reply
    inbox = client.get("/api/invitations?status=pending", headers=ahmed).json()["data"]["items"]
    inv = next(i for i in inbox if i["request_id"] == rid)
    assert inv["hospital_name"] == "City General Hospital (Demo)"
    r = client.post(f"/api/invitations/{inv['id']}/respond", headers=ahmed, json={
        "response": "accepted", "message": "Yes I can come tomorrow after 9, but I had a fever last week"})
    assert r.status_code == 200, r.text
    analysis = r.json()["data"]["invitation"]["response_analysis"]
    assert analysis["conflicts_with_deadline"] is True and "fever" in analysis["concerns"]
    assert analysis["needs_staff_review"] is True
    # Responding twice is rejected
    again = client.post(f"/api/invitations/{inv['id']}/respond", headers=ahmed, json={"response": "declined"})
    assert again.status_code == 409

    # Follow-up: the late acceptance does not count -> alternatives suggested for approval
    detail = client.get(f"/api/requests/{rid}", headers=hosp).json()["data"]
    assert detail["progress"]["accepted_at_risk"] == 1 and detail["progress"]["accepted"] == 0
    assert detail["status"] == "awaiting_approval"
    suggested = client.get(f"/api/requests/{rid}/matches?status=suggested", headers=hosp).json()["data"]["items"]
    assert suggested, "earlier suggestions should be offered for approval"

    # Staff rejects all remaining suggestions -> Follow-up Agent searches for NEW alternatives
    r = client.post(f"/api/requests/{rid}/approve-matches", headers=hosp,
                    json={"reject_ids": [m["id"] for m in suggested]})
    assert r.status_code == 200, r.text
    after = client.get(f"/api/requests/{rid}/timeline", headers=hosp).json()["data"]
    follow_actions = {e["title"] for e in after if e["kind"] == "audit"}
    assert {"followup.alternatives_suggested", "workflow.escalated"} & follow_actions
    new_suggested = client.get(f"/api/requests/{rid}/matches?status=suggested", headers=hosp).json()["data"]["items"]
    assert not ({m["id"] for m in new_suggested} & {m["id"] for m in suggested})

    # A donor cannot answer someone else's invitation
    other_inv = next(i for i in client.get(f"/api/invitations?request_id={rid}", headers=hosp).json()["data"]["items"]
                     if i["id"] != inv["id"])
    assert client.post(f"/api/invitations/{other_inv['id']}/respond", headers=ahmed,
                       json={"response": "accepted"}).status_code == 404

    # 5. Timeline, agent runs, audit log, analytics
    timeline = client.get(f"/api/requests/{rid}/timeline", headers=hosp).json()["data"]
    agents_seen = {e["details"]["agent_name"] for e in timeline if e["kind"] == "agent_run"}
    assert {"request_analysis", "priority_manager", "donor_matching", "coordination", "follow_up"} <= agents_seen
    actions = {e["title"] for e in timeline if e["kind"] == "audit"}
    assert {"request.created", "approval.granted", "invitation.created", "invitation.accepted"} <= actions

    runs = client.get(f"/api/agents/runs?request_id={rid}", headers=admin).json()["data"]
    assert runs["total"] >= 6
    logs = client.get("/api/agents/audit-logs?action=invitation", headers=admin).json()["data"]
    assert logs["total"] >= 3
    assert client.get("/api/agents/audit-logs", headers=hosp).status_code == 403

    ov = client.get("/api/analytics/overview", headers=admin).json()["data"]
    assert ov["demo_data"] is True and ov["total_requests"] >= 4 and ov["invitations_accepted"] >= 2
    groups = client.get("/api/analytics/blood-groups", headers=admin).json()["data"]
    assert len(groups) == 8
    assert client.get("/api/analytics/invitations", headers=hosp).json()["data"]["total"] == 2

    # 6. Timeout sweep: expire the remaining pending invitation
    db = SessionLocal()
    pending = db.query(Invitation).filter(Invitation.request_id == uuid.UUID(rid),
                                          Invitation.status == "pending").all()
    for p in pending:
        p.sent_at = utcnow() - timedelta(hours=3)
    db.commit()
    db.close()
    r = client.post("/api/agents/follow-up/run", headers=admin)
    assert r.json()["data"]["expired_invitations"] >= 1

    # 7. Manual close by staff
    r = client.patch(f"/api/requests/{rid}", headers=hosp, json={"status": "closed"})
    assert r.status_code == 200 and r.json()["data"]["status"] == "closed"
    assert client.post(f"/api/requests/{rid}/run-workflow", headers=hosp).status_code == 409


def test_donor_profile_and_availability(client):
    ahmed = login(client, "donor@bloodbridge.demo")
    me = client.get("/api/donors/me", headers=ahmed).json()["data"]
    assert me["blood_group"] == "O+" and me["demo_eligibility"]["donation_history"]
    r = client.patch(f"/api/donors/{me['id']}/availability", headers=ahmed,
                     json={"availability": "temporarily_unavailable"})
    assert r.status_code == 200 and r.json()["data"]["availability"] == "temporarily_unavailable"
    fatima = login(client, "donor2@bloodbridge.demo")
    assert client.patch(f"/api/donors/{me['id']}/availability", headers=fatima,
                        json={"availability": "available"}).status_code == 403
    admin = login(client, "admin@bloodbridge.demo")
    lst = client.get("/api/donors?blood_group=O%2B&page_size=5", headers=admin).json()["data"]
    assert lst["total"] >= 1 and len(lst["items"]) <= 5
