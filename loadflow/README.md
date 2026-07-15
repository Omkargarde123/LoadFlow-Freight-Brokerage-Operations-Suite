# LoadFlow — Freight Brokerage Operations Suite

A working prototype of the LoadFlow brief: Broker/Carrier/Shipper accounts,
admin-defined RBAC, org + object-level scoping enforced server-side, a load
state machine with audit trail, carrier compliance auto-flagging, and
versioned rate confirmations.

## Stack (and why)

- **Backend: Python / FastAPI** — fast to scaffold a real RBAC + state-machine
  API with typed request/response models (Pydantic) and automatic docs
  (`/docs`), which made it easy to sanity-check every endpoint by hand while
  building.
- **DB: SQLite via SQLAlchemy ORM** — zero setup, and the ORM gives real
  foreign keys / relationships instead of hand-rolled joins, which matters
  for an audit-trail-heavy domain like this.
- **Frontend: React (Vite) + react-router** — small, fast dev loop; no need
  for SSR/routing-on-the-server for an internal ops tool.
- **Auth: JWT (python-jose) + bcrypt** — stateless auth that's trivial to
  attach to every API-layer permission check.

## Deploying as one service (single URL)

The backend serves the built frontend directly (`frontend/dist`), and all
API routes live under `/api` to avoid colliding with the React app's
client-side routes (`/loads`, `/staff`, `/compliance`, `/audit` exist on
both sides). One deploy, one URL, no CORS to configure.

**Render.com (free tier), Web Service:**
- Root Directory: `.` (repo root)
- Build Command: `cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt`
- Start Command: `cd backend && python seed_demo.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

That's it — visiting the Render URL serves the app, and it talks to its own
`/api` on the same origin automatically.

## Running it

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python3 seed_demo.py       # creates loadflow.db with demo accounts (idempotent-safe: skips if DB already has users)
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev     # http://localhost:5173, talks to http://localhost:8000 (see .env.development)
```

### Demo accounts (all password: `password123`)
| Role | Email |
|---|---|
| Broker Admin (Summit Freight) | admin@summitfreight.com |
| Broker Dispatcher (Dispatcher role: assign+rate+status, no staff.manage) | dispatcher@summitfreight.com |
| Carrier Admin, compliant fleet (Ironclad Trucking) | admin@ironcladtrucking.com |
| Carrier Driver (Ironclad) | driver@ironcladtrucking.com |
| Carrier Admin, **non-compliant** fleet (Rustbelt Haulers — expired insurance, only Flatbed-approved) — use this to trigger the compliance HOLD | admin@rustbelthaulers.com |
| Shipper | ops@acmemanufacturing.com |

Two loads are pre-seeded (Chicago→Dallas Dry Van, Atlanta→Miami Reefer) so
the load board isn't empty on first login. To reset, delete `backend/loadflow.db`
and re-run `seed_demo.py`.

## How the RBAC is actually built (not hardcoded)

- Fixed permission catalog in `backend/app/models.py`
  (`load.create`, `load.assign_carrier`, `load.override_compliance_flag`,
  `rate.confirm`, `load.update_status`, `staff.manage`, `pod.upload`).
- `Role` rows are admin-defined bundles of those permissions (created via the
  Staff & Roles screen — see `POST /roles`). Every endpoint checks
  `permission in current_user.effective_permissions`, never a role name
  (`backend/app/deps.py::require_permission`).
- **Bootstrap vs. invite:** the *only* way an Admin account is created is
  `POST /auth/register-org`, which creates an Org + its first Admin
  atomically (self-service signup). There is no public staff-signup route —
  Admins create staff via `POST /staff` with a temp password they hand off
  out-of-band (no email sending in this demo).
- **Org scoping:** every load/staff/role query is filtered by
  `current_user.org_id`; a Broker never sees Carrier org data or vice versa.
- **Object-level scoping:** Shippers only see loads where they're the
  shipper; Carrier staff only see loads assigned to their carrier org
  (`backend/app/routers/loads.py::_scope_query`) — independent of what
  permissions they hold.
- **API-layer enforcement:** confirmed by direct testing — e.g. a Dispatcher
  (no `staff.manage`) hitting `GET /staff` directly gets a 403, not just a
  hidden button.
- **Permission-denied logging:** every 403 is written to a
  `permission_denied_log` table and to stdout (`backend/app/deps.py`),
  viewable by Admins under Audit Log.

## Compliance auto-flagging

On carrier assignment (`POST /loads/{id}/assign-carrier`), LoadFlow checks
the carrier's compliance record for expired insurance, non-active MC/DOT
status, and equipment/commodity mismatches. Any hit sets
`compliance_flag = true` with a human-readable reason, and blocks rate
confirmation / status advancement past "Carrier Assigned" until an Admin
with `load.override_compliance_flag` explicitly overrides it. Try assigning
**Rustbelt Haulers** to a load to see this trigger.

## What's implemented (must-haves)

- 3 account types, admin-defined roles, server-enforced RBAC with org +
  object scoping
- Load CRUD, full 8-state machine, timestamped/attributed audit trail
- Carrier compliance CRUD + auto-flagging that blocks progression
- Rate confirmation with versioning (reconfirm creates a new version;
  historical loads keep whichever version was current when they progressed)
- Dashboards per account type, load board search/filter (status, origin,
  destination, equipment)

## Stretch implemented

- **Audit log viewer** (Admin-only screen listing permission-denied attempts)

## Stretch not implemented (with more time)

- **POD upload/viewer** — the `pod.upload` permission and status slot exist,
  but there's no file storage wired up. Next step: an S3-compatible object
  store (or local disk for the demo) + a `pod_documents` table linked to the
  load.
- **Compliance expiry renewal alerts** — the data (`insurance_expiry`) is
  there; would add a scheduled check (or a computed "expiring soon" badge on
  the Carrier's own dashboard) rather than a real notification pipeline.

## Assumptions made

- Shippers self-signup directly (no org, no invite) since the brief has them
  as individual/business accounts with no sub-roles.
- Staff invites hand off a temp password out-of-band rather than sending
  real email, since there's no mail service in scope.
- The generic status-advance endpoint only allows single-step-forward
  transitions; "Carrier Assigned → Rate Confirmed" is deliberately excluded
  from that generic endpoint and only reachable through the dedicated
  rate-confirmation flow, so a rate confirmation record always exists before
  a load can be marked Rate Confirmed.
- One compliance record per carrier org (not per-load); a Broker can view
  any carrier's record when picking who to assign, but only that carrier's
  own Admin can edit it.

## AI tool usage

Built end-to-end with Claude (Claude Code / Claude in a container-style dev
environment): scaffolding the FastAPI app and data model from the brief,
iterating on the RBAC dependency design, and building the React UI page by
page. Reviewed and ran a live integration test against the running API
(assign carrier → compliance flag trip → blocked rate confirmation →
override → success) before touching the frontend, to make sure the backend
contract was right first.
