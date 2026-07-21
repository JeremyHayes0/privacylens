# PrivacyLens — Backend

PrivacyLens is a self-hosted web application that scans websites for
observable privacy and security configurations — cookies, third-party
trackers, security headers, HTTPS/TLS setup, and the presence of
privacy policies, terms of service, and consent banners — and reports
them as structured, non-legal findings ("Observation," "Potential
Issue," "Detected Configuration," "Recommendation"). It does not
provide legal advice or compliance determinations.

This README covers the **backend** service only.

## Current status

Three milestones are complete:

1. **Authentication foundation** — application bootstrap, configuration,
   database connectivity, the `User` model, and JWT-based authentication
   with role-based access control.
2. **Core scanning workflow foundation** — organizations (multi-tenancy),
   targets (websites to monitor), and scans (the lifecycle record for a
   scan request).
3. **Scan worker and checks engine** — an RQ-backed background worker
   actually processes queued scans: it fetches the target, runs the
   registered checks against it, writes `Finding` rows, and transitions
   the scan to `completed` or `failed`. Five check categories exist so
   far: HTTPS/TLS, security headers, cookie security flags, privacy
   policy link detection, and Terms of Service link detection.
   Third-party tracker detection and consent-banner detection are not
   yet implemented — both need to observe a *rendered* page (via
   something like Playwright) rather than a single HTTP fetch. See
   "What's not implemented yet" below.

## Technology stack

| Layer | Choice |
|---|---|
| API framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM | SQLAlchemy 2.0 (declarative, typed `Mapped[...]` columns) |
| Migrations | Alembic |
| Database | PostgreSQL |
| Auth | JWT access tokens (PyJWT), bcrypt password hashing |
| Config | pydantic-settings (env-var driven) |
| HTTP fetching (scanning) | httpx |
| Background queue | Redis + RQ |
| Testing | pytest, FastAPI's `TestClient`, SQLite in-memory for test isolation |

## Architecture

Routes are intentionally thin. The flow for any request is:

```
route (app/api/v1/routes_*.py)
  -> validates input via a Pydantic schema (app/schemas/)
  -> calls a service function (app/services/) for business logic
       -> which calls the CRUD layer (app/crud/) for raw DB access
            -> which operates on ORM models (app/models/)
  -> translates the result (or a raised domain exception) into an HTTP response
```

No route handler contains a SQLAlchemy query directly, and no service
function knows anything about FastAPI or HTTP status codes — that
separation is what makes the business logic (e.g. "is this email
already registered?", "do these credentials match?") unit-testable
without spinning up the web framework at all.

### Domain model

```
Organization
    └── User            (every user belongs to exactly one organization)
    └── Target           (a website the organization has asked to monitor)
          └── Scan       (one request to scan a target, and its lifecycle)
                └── Finding   (one observation produced by one check during one scan)
```

- **Organization** is the tenant boundary. Every `User` and every
  `Target` belongs to exactly one organization, and access control
  throughout the API is enforced by comparing `organization_id` —
  never by trusting a resource id alone. There's no invite flow yet,
  so today every self-registered user creates (and becomes the admin
  of) their own new organization; a Phase 2 invite flow will let an
  existing admin add teammates to it instead.
- **Target** is a website an organization wants PrivacyLens to watch.
  Its URL is validated and normalized at two layers on purpose (the
  Pydantic schema at the API boundary, and the SQLAlchemy model
  itself) — see `app/models/target.py` for why that's deliberate
  defense in depth rather than duplication.
- **Scan** is a lifecycle record: a request to scan a target, and its
  current status (`queued` → `running` → `completed`/`failed`).
- **Finding** is one observation produced by one check during one
  scan — a category (`https`, `headers`, ...), a non-legal
  `finding_type` (`potential_issue` / `observation` /
  `detected_configuration` / `recommendation` — never a compliance
  verdict), a severity, and JSON `evidence` whose shape is
  category-specific (a header's name/value, a certificate's expiry
  date). See `app/models/finding.py` for why `finding_type` has no
  value that could read as a legal conclusion — that's a deliberate,
  schema-level constraint, not just UI copy.

**Scans are asynchronous by design, not by accident.** `POST
/api/v1/targets/{id}/scans` returns `202 Accepted` with a scan id
immediately — it does not perform any scanning inline, because
scanning a live website (loading it, inspecting network traffic,
checking headers) is a slow, I/O-bound operation that has no business
blocking an HTTP request/response cycle. The request handler enqueues
the scan (`app/core/queue.py`) and returns; a separate RQ worker
process (`worker_entrypoint.py`, executing `app/worker/tasks.py`)
picks it up, fetches the target once (`app/scanning/fetcher.py`), runs
every registered check against that single fetch
(`app/scanning/registry.py`), persists the resulting `Finding` rows,
and transitions the scan to `completed` or `failed`
(`app/services/scan_orchestrator.py`). Callers poll
`GET /api/v1/scans/{id}` for status and
`GET /api/v1/scans/{id}/findings` for results — both work correctly
whether the worker has processed the scan yet or not (an unprocessed
scan simply has an empty findings list, which is a valid `200`, not a
`404`).

**The checks engine currently covers five categories: HTTPS/TLS,
security headers, cookies, privacy policy, and Terms of Service.**
Every check is a pure function over an already-fetched `ScanContext` —
see `app/scanning/base_check.py` for why that separation (one fetch,
many independent checks) is the whole point of the abstraction. The
cookie and link-detection checks needed two small, deliberately pure
helper modules to feed them data the earlier checks didn't need:
`app/scanning/cookie_utils.py` (parses raw `Set-Cookie` header strings
into name/Secure/HttpOnly/SameSite, independent of any HTTP library)
and `app/scanning/html_utils.py` (extracts every `<a href>` from the
page body using the standard library's `html.parser`, deliberately
not a regex or a new dependency like BeautifulSoup). Both are called
once by the fetcher and the results attached to `ScanContext`, so
`CookiesCheck`, `PrivacyPolicyCheck`, and `TermsOfServiceCheck` never
touch raw headers or HTML themselves — consistent with every other
check in the registry. Adding tracker or consent-banner detection
later is a new `BaseCheck` subclass plus one line in the registry, not
a change to the orchestrator.

## Folder structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app instance, health check, router mounting
│   ├── core/
│   │   ├── config.py            # pydantic-settings configuration
│   │   ├── database.py          # engine, session factory, get_database_session dependency
│   │   ├── security.py          # password hashing, JWT creation/validation
│   │   └── queue.py             # Redis/RQ connection + enqueue_scan (only module that knows about the queue)
│   ├── api/
│   │   ├── deps.py              # get_current_user, require_role
│   │   └── v1/
│   │       ├── __init__.py      # api_router aggregation
│   │       ├── routes_auth.py   # /auth/register, /auth/login, /auth/me
│   │       ├── routes_targets.py # /targets CRUD (org-scoped)
│   │       └── routes_scans.py   # /targets/{id}/scans, /scans/{id}, /scans/{id}/findings
│   ├── models/
│   │   ├── __init__.py           # imports all models -- see its docstring
│   │   ├── organization.py       # Organization model (tenant boundary)
│   │   ├── user.py               # User model, UserRole enum
│   │   ├── target.py             # Target model + URL normalization/validation
│   │   ├── scan.py               # Scan model, ScanStatus enum (lifecycle)
│   │   └── finding.py            # Finding model, FindingCategory/Type/Severity enums
│   ├── schemas/
│   │   ├── user.py               # UserCreate, UserRead
│   │   ├── auth.py               # LoginRequest, Token
│   │   ├── target.py             # TargetCreate, TargetRead
│   │   ├── scan.py               # ScanCreateResponse, ScanRead
│   │   └── finding.py            # FindingRead (read-only -- findings are never client-created)
│   ├── crud/
│   │   ├── user.py               # thin DB access functions
│   │   ├── organization.py       # thin DB access functions
│   │   ├── target.py             # thin DB access functions
│   │   ├── scan.py               # thin DB access functions
│   │   └── finding.py            # thin DB access functions
│   ├── services/
│   │   ├── auth_service.py       # registration/authentication business logic
│   │   ├── target_service.py     # target creation + organization-scoped access control
│   │   ├── scan_service.py       # queued scan creation (+ enqueue) + organization-scoped access control
│   │   └── scan_orchestrator.py  # runs one scan end to end: fetch -> checks -> findings -> status
│   ├── scanning/                 # the checks engine -- pure, no DB, no HTTP framework knowledge
│   │   ├── context.py            # ScanContext, CookieObservation, LinkObservation
│   │   ├── fetcher.py            # the ONLY module that makes the outbound network request
│   │   ├── cookie_utils.py       # pure Set-Cookie header parsing (name/Secure/HttpOnly/SameSite)
│   │   ├── html_utils.py         # pure <a href> extraction via stdlib html.parser
│   │   ├── base_check.py         # BaseCheck ABC, FindingDraft
│   │   ├── registry.py           # REGISTERED_CHECKS -- the list the orchestrator runs
│   │   └── checks/
│   │       ├── https_check.py         # HTTPS usage + TLS certificate expiry
│   │       ├── headers_check.py       # presence of common security response headers
│   │       ├── cookies_check.py       # Secure/HttpOnly/SameSite flags per cookie
│   │       └── policy_links_check.py  # PrivacyPolicyCheck + TermsOfServiceCheck (link heuristics)
│   └── worker/
│       └── tasks.py              # run_scan_task -- what an RQ worker process actually executes
├── worker_entrypoint.py          # `python worker_entrypoint.py` starts an RQ worker
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 0001_create_users_table.py
│       ├── 0002_add_organizations_targets_scans.py
│       └── 0003_add_findings_table.py
├── tests/
│   ├── conftest.py                # test DB + TestClient fixtures + enqueue_scan stub
│   ├── unit/
│   │   ├── test_security.py       # hashing/JWT, no DB or app needed
│   │   ├── test_checks.py         # every check against a hand-built ScanContext, no network/DB
│   │   ├── test_cookie_utils.py   # Set-Cookie parsing, no network/DB
│   │   ├── test_html_utils.py     # link extraction, no network/DB
│   │   └── test_queue.py          # enqueue_scan's contract, no live Redis needed
│   └── integration/
│       ├── test_health.py
│       ├── test_auth.py
│       ├── test_targets.py        # target CRUD + org isolation
│       ├── test_scans.py          # scan creation/status + org isolation
│       └── test_scan_orchestrator.py  # fetch mocked, real DB -- full queued->completed/failed path
├── .env.example
├── alembic.ini
└── requirements.txt
```

## Local setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ running locally (or via Docker)
- Redis 6+ running locally (or via Docker) — required for the scan
  worker; the API itself will start without it, but `POST
  /targets/{id}/scans` will fail loudly (a 500) if Redis is
  unreachable when a scan is created. See the "Security notes" section
  for why that's a deliberate choice rather than a silent failure.

### 1. Create and activate a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` and set at minimum:
- `DATABASE_URL` — point it at your local Postgres instance
- `REDIS_URL` — point it at your local Redis instance (the
  `.env.example` default, `redis://localhost:6379/0`, works for a
  plain local `redis-server` with no auth)
- `JWT_SECRET_KEY` — generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

### 4. Create the database

```bash
createdb privacylens
```

(Adjust for however you manage local Postgres — Docker, Homebrew, etc.
If you have a `docker-compose.yml` with `db`/`redis` services defined
at the project root, `docker compose up -d db redis` covers both at
once.)

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`. Interactive docs:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- Health check: `http://localhost:8000/health`

### 7. Run the scan worker

In a **separate terminal** (same virtual environment, same `.env`):

```bash
python worker_entrypoint.py
```

Without this running, scans will be created successfully and sit in
`queued` forever — the API process only ever enqueues a scan, it never
runs one. The worker is what actually fetches the target, runs the
registered checks, writes findings, and moves the scan to `completed`
or `failed`.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `REDIS_URL` | no | `redis://localhost:6379/0` | Redis connection string, shared by the API (enqueueing) and the worker (consuming) |
| `JWT_SECRET_KEY` | yes | — | Secret used to sign JWTs. Long, random, never committed. |
| `JWT_ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `15` | Access token lifetime |
| `ENVIRONMENT` | no | `development` | Free-text environment label |

## Running tests

Tests run against an in-memory SQLite database via dependency
overrides, so no running Postgres instance is required to run the
test suite. Redis and outbound network access aren't required either:
an autouse fixture in `conftest.py` stubs `enqueue_scan` for every
test, and the orchestrator/checks tests mock `fetch_target` rather
than making a real request. `tests/unit/test_queue.py` and
`tests/unit/test_checks.py` verify those pieces' own contracts in
isolation, with no live Redis or network needed even there.

```bash
pytest
```

Run only unit tests (no app/DB wiring, fastest):

```bash
pytest tests/unit
```

Run only integration tests (spin up the FastAPI app + test DB):

```bash
pytest tests/integration
```

## Creating a new migration

After changing a model in `app/models/`:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Always review the autogenerated migration before running it —
autogenerate is a helpful starting point, not a guarantee of
correctness (it won't detect every kind of change, e.g. some
constraint renames).

## API endpoints implemented so far

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/health` | no | Liveness check |
| POST | `/api/v1/auth/register` | no | Create a new user + a new organization they administer |
| POST | `/api/v1/auth/login` | no | Exchange credentials for a JWT access token |
| GET | `/api/v1/auth/me` | yes (Bearer token) | Return the authenticated user |
| POST | `/api/v1/targets` | yes (admin/analyst) | Add a website to monitor |
| GET | `/api/v1/targets` | yes (any role) | List targets in the caller's organization |
| GET | `/api/v1/targets/{id}` | yes (any role) | Get one target (404 if outside caller's org) |
| DELETE | `/api/v1/targets/{id}` | yes (admin/analyst) | Soft-delete (deactivate) a target |
| POST | `/api/v1/targets/{id}/scans` | yes (admin/analyst) | Create + enqueue a scan — returns `202 Accepted` |
| GET | `/api/v1/scans/{id}` | yes (any role) | Get scan status (404 if outside caller's org) |
| GET | `/api/v1/scans/{id}/findings` | yes (any role) | List a scan's findings (empty list if still queued/running) |

## Security notes

- Passwords are hashed with bcrypt (random per-password salt, tunable
  work factor) and are never logged or returned in any response.
- Access tokens are short-lived JWTs (15 minutes by default). They are
  stateless, so a server-side refresh-token/revocation mechanism is
  the natural next step rather than simply lengthening this window.
- `GET /auth/me` re-reads the user's role and active status from the
  database on every request rather than trusting the JWT payload
  alone, so a role change or deactivation takes effect immediately.
- Login failures return an identical error for "no such user" and
  "wrong password," to avoid leaking which emails have registered
  accounts.
- `UserCreate.password` enforces a minimum length at the API boundary
  via Pydantic; a full password-strength policy is a product decision
  left for later.
- **Organization isolation is enforced at a single choke point per
  resource** (`target_service._assert_same_organization`,
  `scan_service.get_scan_for_user`) rather than repeated inline in
  every route. Every route that resolves a target or scan by id goes
  through one of these functions, so the check can't be silently
  skipped by a new endpoint that forgets to add it.
- **A target that exists in another organization returns the same 404
  as one that doesn't exist at all.** A distinct 403 would confirm to
  a caller that a given id belongs to *someone else's* org, which is
  itself a small enumeration leak — the same reasoning already applied
  to login's "incorrect email or password" message.
- **Target URLs are restricted to `http://`/`https://` and validated at
  two layers**: the Pydantic schema (fast, friendly 422 at the API
  boundary) and the SQLAlchemy model's own `@validates("url")` (so the
  invariant holds even for a future code path — an admin script, a
  data import — that doesn't go through the API). This is a real,
  active SSRF guardrail now, not a future one: the fetcher
  (`app/scanning/fetcher.py`) is the only code that makes the outbound
  request, and it can never be handed a `file://` or internal-scheme
  target because nothing upstream of it can construct one.
- **Creating, deactivating, or scanning a target requires the admin or
  analyst role**; viewers can read but not mutate. This is the first
  real use of the `require_role` dependency built in the previous
  milestone for something other than illustration.
- **The fetcher identifies itself with an explicit `User-Agent`**
  (`PrivacyLensBot/0.1 (compliance-scanner; not a browser)`) rather
  than spoofing a real browser — a site operator inspecting their
  access logs should be able to tell PrivacyLens's traffic apart from
  a regular visitor.
- **The fetcher enforces a hard 10-second timeout** on both the HTTP
  request and the separate TLS-certificate-reading connection. A
  target that hangs or stalls fails the scan (`FAILED`, with an
  `error_message`) rather than tying up a worker process indefinitely.
- **`FindingType` has no value that reads as a legal conclusion** —
  see `app/models/finding.py`. `potential_issue`, `observation`,
  `detected_configuration`, and `recommendation` are the only options;
  there is no `violation` or `non_compliant` a check could reach for.
  This is schema-level enforcement of PrivacyLens's core design
  constraint, not just a disclaimer in the UI.
- **`enqueue_scan` failures are not swallowed.** If Redis is
  unreachable when a scan is created, the request fails loudly (a
  `500`) rather than silently leaving a `queued` scan that will never
  be picked up. A caller finding out immediately that something is
  wrong is better than a scan silently going nowhere.

## What's not implemented yet

By design, at this stage: refresh tokens and logout/revocation, rate
limiting, audit logging middleware, an invite flow for adding a second
user to an existing organization, and PDF/CSV report export. Within
the scanning engine, third-party tracker detection and consent-banner
detection are the two remaining check categories from the project
blueprint — both need to observe a *rendered* page (scripts executed,
DOM as the browser would build it) rather than a single HTTP fetch,
which means they'll need something like Playwright rather than the
current httpx-based fetcher; that's a bigger lift than the other five
checks and is the natural next scanning-engine milestone. Adding
either is still a new `BaseCheck` subclass and one line in the
registry, not a change to the orchestrator. Scan scheduling/recurrence,
scan diffing between two scans of the same target, and score/rubric
calculation (a "technical posture score," never a "compliance score"
— see the project blueprint's guardrails on this point) are also not
yet implemented. See the project blueprint's Phase 1–3 roadmap for
sequencing.
