# BloodBridge AI – Backend

FastAPI + PostgreSQL backend for BloodBridge AI: request analysis, operational priority, donor
matching, human-approved simulated invitations, follow-up and analytics, with every agent step
recorded for the timeline and audit log.

> Hackathon prototype. **Synthetic data only.** No real SMS/calls/emails. No clinical decisions:
> the match score is an operational ranking, and acceptance of an invitation is not a donation.

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

docker compose -f docker-compose.dev.yml up -d      # local Postgres on :5432
alembic upgrade head                                # create tables
python -m app.db.seed                               # synthetic demo data (--reset to wipe)
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs (click **Authorize**, paste the `access_token` from login)
- Health: http://localhost:8000/api/health
- Tests: `pytest -q` (uses a throwaway SQLite DB; set `TEST_DATABASE_URL` to run against Postgres)

### Demo logins (password `Demo@123`)

| Email | Role | Notes |
|---|---|---|
| admin@bloodbridge.demo | admin | sees everything |
| hospital@bloodbridge.demo | hospital | City General Hospital (Demo), Faisalabad |
| hospital2@bloodbridge.demo | hospital | Lahore Demo Medical Centre |
| donor@bloodbridge.demo | donor | Ahmed Khan, O+, Faisalabad (ranks high for O+) |
| donor2@bloodbridge.demo | donor | Fatima Noor, O-, Faisalabad (use for a decline) |

The seed also creates 62 random synthetic donors around Faisalabad, Lahore, Jhang, Chiniot and
Sargodha, plus 3 requests: one already completed, one `awaiting_approval`, and one `submitted`
(REQ-DEMO-002) for running the workflow live.

## Agent workflow

```
submitted --run-workflow--> processing
   Request Analysis Agent  validate + normalise (+ cross-check the free-text description)
   Priority Manager        transparent score -> low / medium / high / critical
   Donor Matching Agent    SQL filters + scored candidates (radius widens 25 -> 50 -> 100 km)
   Analytics Agent         demand snapshot
--> awaiting_approval        (HUMAN GATE: nothing is sent before approval)
--approve-matches-->
   Coordination Agent      simulated in-app invitations (no duplicates, ever)
--> inviting_donors
--donor responds / invitation times out-->
   Follow-up Agent         reads the donor's reply, recounts, decides:
                           partially_fulfilled | fulfilled (workflow state only)
                           | awaiting_approval (more donors needed: earlier or new suggestions)
                           | escalated to admin (no candidates left)
```

Where the LLM (Vultr Serverless Inference) is used: **only** to read messy text — the
`/requests/analyze-text` endpoint, the description cross-check, and donor replies
("yes but only after 9 tomorrow, had a fever last week" -> flags deadline conflict + staff
review). Output is validated with Pydantic, and if the key is missing or the call fails,
deterministic rules take over. Matching, priority and status changes never use the LLM.

Enable it by setting `VULTR_INFERENCE_API_KEY` and `VULTR_INFERENCE_MODEL` in `.env`;
`/api/health` reports `llm_enabled`.

The Follow-up Agent also runs in the background every `FOLLOW_UP_INTERVAL_SECONDS`, expiring
invitations older than `INVITATION_TIMEOUT_MINUTES` and searching for alternatives. Admins can
trigger it at once with `POST /api/agents/follow-up/run` (handy in the demo).

## API (base `/api`)

Every response uses one envelope:
```json
{"success": true,  "message": "Request created successfully", "data": {...}}
{"success": false, "message": "Validation failed", "errors": [{"field": "blood_group", "message": "..."}]}
```
Lists are paginated with `?page=1&page_size=20` and return
`data: {"items": [...], "total": n, "page": 1, "page_size": 20}`.
Auth: `Authorization: Bearer <access_token>`.

| Method | Endpoint | Who | Purpose |
|---|---|---|---|
| POST | /auth/register | public | Register hospital or donor (`role`, `city`, `hospital_name` / `blood_group`) |
| POST | /auth/login | public | Returns `access_token` + `me` |
| GET | /auth/me | any | `{user, hospital, donor}` |
| POST | /requests/analyze-text | hospital, admin | Free text -> structured fields to pre-fill the form (saves nothing) |
| POST | /requests | hospital | Create request (`auto_run_workflow: true` runs agents immediately) |
| GET | /requests | hospital (own), admin | Filters: `status` (comma list), `urgency`, `priority`, `blood_group`, `search`; `sort=created\|priority\|deadline` (`priority` = work queue) |
| GET | /requests/{id} | hospital (own), admin | Detail + `hospital_name` + `progress` counts |
| PATCH | /requests/{id} | hospital (own), admin | Edit details (resets to submitted) or set `status`: fulfilled / closed / cancelled |
| POST | /requests/{id}/run-workflow | hospital (own), admin | Run analysis -> priority -> matching |
| GET | /requests/{id}/matches | hospital (own), admin | Candidates with score, distance, reasons, `invitation_status`; filter `status` |
| POST | /requests/{id}/approve-matches | hospital (own), admin | `{"approve_ids": [...], "reject_ids": [...]}` -> invitations |
| GET | /requests/{id}/timeline | hospital (own), admin | Agent runs + audit events in time order |
| GET | /donors | admin | Filters: `blood_group`, `availability`, `city`, `search` |
| GET / PATCH | /donors/me | donor | Profile (incl. synthetic donation history in `demo_eligibility`) |
| PATCH | /donors/{id}/availability | donor (self), admin | `available` / `temporarily_unavailable` / `unavailable` |
| GET | /invitations | donor (own), hospital (own requests), admin | Filters: `status`, `request_id` |
| GET | /invitations/{id} | same | Invitation + request info |
| POST | /invitations/{id}/respond | donor (own) | `{"response": "accepted"\|"declined", "message": "optional free text"}` |
| GET | /agents/runs | hospital (own), admin | Agent monitor; filters `request_id`, `agent_name`, `status` |
| GET | /agents/runs/{id} | hospital (own), admin | One run with input/output |
| GET | /agents/audit-logs | admin | Audit viewer; filters `request_id`, `action` (prefix), `actor_type` |
| POST | /agents/follow-up/run | admin | Run the follow-up timeout sweep now |
| GET | /analytics/overview | hospital (own), admin | Counts for dashboard cards |
| GET | /analytics/blood-groups | hospital (own), admin | Demand vs donors per blood group |
| GET | /analytics/invitations | hospital (own), admin | Status counts, acceptance rate, avg response time |

Notes for the frontend:
- Request statuses: `draft, submitted, processing, awaiting_approval, inviting_donors, partially_fulfilled, fulfilled, closed, cancelled`. Show `status_note` under the badge — it explains what happens next.
- `progress` on request detail: `accepted, accepted_at_risk, declined, pending, expired, units_requested, still_needed, suggested_awaiting_approval`.
- Invitation `response_analysis` (when the donor typed a message): `available_from, concerns[], summary, conflicts_with_deadline, needs_staff_review, source (llm|rules)`.
- Timeline item: `{kind: "agent_run"|"audit", id, at, title, status, summary, details}`.
- A hospital requesting another hospital's request gets 404; wrong role gets 403.

## Additions to the team guide's schema

Kept every table and column from the guide, plus these (needed for the dashboards and safety rules):
- `blood_requests`: `title`, `contact_info` (demo), `priority_score`, `priority_reason`, `status_note`, `updated_at`
- `donor_matches`: `distance_km`, `created_at`; unique (`request_id`, `donor_id`)
- `invitations`: `match_id`, `response_message`, `response_analysis`, status `expired`; unique (`request_id`, `donor_id`) so retries never duplicate
- `agent_runs`: `output_data` (JSON for the agent monitor)
- `audit_logs`: `actor_type`, `request_id` (for the per-request timeline)
- extra endpoints: `/requests/analyze-text`, `/agents/audit-logs`, `/agents/follow-up/run`

## Structure

```
backend/
  app/
    main.py              app, CORS, error envelope, background follow-up loop
    core/                settings, JWT + bcrypt, auth/role dependencies, response envelope
    db/                  engine/session, seed.py
    models/              SQLAlchemy models (8 tables)
    schemas/             Pydantic request/response models
    api/                 routers: auth, requests, donors, invitations, agents, analytics
    agents/              request_analysis, priority_manager, donor_matching, coordination,
                         follow_up, analytics_agent, orchestrator (supervisor), llm (Vultr client)
    services/            blood-group demo rules, geo (city table + haversine), audit helper
  alembic/               migrations (0001 initial schema)
  tests/                 rule tests + full end-to-end workflow test
  Dockerfile             runs `alembic upgrade head` then uvicorn on :8000
```

## For deployment

- Build `backend/Dockerfile`; it listens on port 8000 and applies migrations on start.
- Required env: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS` (the public frontend URL).
  Optional: `VULTR_INFERENCE_API_KEY`, `VULTR_INFERENCE_MODEL`. See `.env.example`.
- Seed once after the first start: `docker compose exec backend python -m app.db.seed`.
- Route `/api/*` from Nginx to the backend container.
