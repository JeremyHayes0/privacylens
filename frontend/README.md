# PrivacyLens — Frontend

A React + TypeScript dashboard for the PrivacyLens backend (see
`../backend`): sign in, add websites to monitor, trigger scans, and
read the resulting findings.

## Local setup

### Prerequisites
- Node.js 20+
- The backend running locally (see `../backend/README.md`) — this app
  is a pure client to that API and has no server component of its own.

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure the API base URL

```bash
cp .env.example .env
```

The default, `http://localhost:8000/api/v1`, matches the backend's
default local setup and usually doesn't need changing.

### 3. Run the dev server

```bash
npm run dev
```

The app is available at `http://localhost:5173`. Register an account
(this creates a new organization and makes you its admin — see the
backend README's auth flow), then add a target and run a scan.

### 4. Run the tests

```bash
npm test
```

Runs the whole suite once (`vitest run`). Use `npm run test:watch` for
a watch-mode run while developing. No backend, database, or network
access is required — see "Testing" below for how that's achieved.

### 5. Build for production

```bash
npm run build
```

Type-checks (`tsc -b`) before bundling — a build that doesn't type-check doesn't produce output.

## Architecture

```
src/
├── api/                  # everything that talks to the backend
│   ├── client.ts         # fetch wrapper: base URL, auth header, error shape
│   ├── client.test.ts
│   ├── types.ts          # TS types mirroring backend Pydantic schemas
│   ├── auth.ts           # /auth/* calls
│   ├── targets.ts        # /targets/* calls
│   └── scans.ts          # /scans/*, /targets/{id}/scans calls
├── context/
│   ├── AuthContext.tsx   # current user, login/register/logout, token lifecycle
│   └── AuthContext.test.tsx
├── hooks/
│   ├── useAsync.ts       # shared loading/error/data fetching pattern
│   └── useAsync.test.ts
├── components/
│   ├── Layout.tsx        # nav rail + content shell
│   ├── ProtectedRoute.tsx
│   ├── Pills.tsx         # FindingTypePill, ScanStatusPill (see "Design" below)
│   ├── FindingCard.tsx
│   └── ScopeBanner.tsx   # the non-legal-advice disclaimer, shown on every report
├── pages/
│   ├── LoginPage.tsx
│   ├── LoginPage.test.tsx
│   ├── RegisterPage.tsx
│   ├── DashboardPage.tsx     # target list + add-target form
│   ├── DashboardPage.test.tsx
│   ├── TargetDetailPage.tsx  # scan trigger + scan history
│   ├── ScanReportPage.tsx    # scan status (polled) + findings by category
│   └── ScanReportPage.test.tsx
├── test/setup.ts          # jest-dom matchers, cleanup between tests
├── styles/global.css     # the entire design token system + all component styles
├── App.tsx                # routing
└── main.tsx                # entrypoint
```

Every page follows the same shape: a page component owns its route,
reads data via `useAsync` (or, for `ScanReportPage`, a small custom
polling effect — see below), and renders through shared components.
There's no state management library — `AuthContext` is the only
context in the app, and every other piece of server state is fetched
per-page rather than cached globally. That's a deliberate scope choice
for an app this size, not an oversight: the natural upgrade path if
the app grew is TanStack Query (co-locating cache invalidation,
background refetch, and request de-duping), which the project
blueprint calls out explicitly for exactly that reason.

### Why polling, not WebSockets, for scan status

`ScanReportPage` polls `GET /scans/{id}` and `GET /scans/{id}/findings`
every 3 seconds while a scan is `queued` or `running`, and stops the
moment it reaches `completed` or `failed`. A scan takes a few seconds
to tens of seconds — polling at a 3-second interval is simple, doesn't
require a WebSocket/SSE endpoint the backend doesn't have yet, and the
staleness window (worst case, 3 seconds) doesn't matter for something
a person is actively looking at.

## Design

The design brief for this app: it's an instrument that observes and
records, not a SaaS product selling itself — that's the whole thesis
behind the backend's `finding_type` taxonomy (Observation / Potential
Issue / Detected Configuration / Recommendation, never a verdict), and
the frontend is built to read the same way.

- **Color**: a blue-tinted ink background (`#0F1417`), not pure black
  and not the warm-cream-plus-terracotta look common to AI-generated
  UI. Severity/status colors are functional (they mean something
  specific), not decorative accents.
- **Type**: IBM Plex Sans for UI text, IBM Plex Mono for anything that
  is *data* — URLs, header names, cookie names, evidence values,
  timestamps, scan/finding ids. The monospace treatment is doing real
  work: it visually marks "this is a fact PrivacyLens observed" versus
  "this is the app talking to you."
- **Signature element**: the finding-type pill (`components/Pills.tsx`)
  and the scan-history ledger (`TargetDetailPage`) are the two places
  the design commits hardest — small, monospace, uppercase, a single
  colored tick per row. Both exist to make the non-legal-verdict
  design constraint *visible*, not just documented in a README.

See `src/styles/global.css` for the full token system (colors, type,
spacing) as CSS custom properties.

## Testing

Vitest + React Testing Library, colocated with the code they test
(`Thing.test.ts(x)` next to `Thing.ts(x)`). Coverage is deliberately
concentrated on the three areas with real logic to get wrong, rather
than spread thin across every component:

- **`api/client.test.ts`** — the fetch wrapper: auth header attachment,
  JSON parsing, and extracting the backend's `{"detail": "..."}` error
  shape into an `ApiError`.
- **`hooks/useAsync.test.ts`** — the shared data-fetching hook every
  page relies on: loading → data, loading → error (both `ApiError` and
  a generic failure), and `reload()`.
- **`context/AuthContext.test.tsx`** — login, a failed login leaving
  the user unset, register-then-login, logout, and clearing an invalid
  stored token on mount without surfacing an error.
- **`pages/LoginPage.test.tsx`** — the backend's error message actually
  reaching the screen, the submit button disabling mid-request, and
  the right payload being sent.
- **`pages/DashboardPage.test.tsx`** — the add-target control's
  visibility by role (this is the RBAC-in-the-UI decision from the
  "Architecture" notes, tested directly), the empty state, a
  successful submission refreshing the list, and a failed submission's
  error message.
- **`pages/ScanReportPage.test.tsx`** — the polling behavior itself:
  that it re-polls after the interval while `queued`/`running`, that
  it stops rescheduling once `completed` (verified by advancing fake
  time further and confirming no additional call), and that findings
  render grouped under their category with the scope banner, while a
  `failed` scan shows its error message with no banner.

Every test mocks the relevant `api/*.ts` module (or, for `client.test.ts`,
`fetch` itself) rather than hitting a real backend — the suite needs no
running server, database, or network access to run. `pages/ScanReportPage.test.tsx`
uses Vitest's fake timers to make the 3-second poll interval
deterministic instead of actually waiting on it.

Not yet covered: `TargetDetailPage`, `RegisterPage`, and the presentational
components (`Pills`, `FindingCard`) in isolation — reasonable next additions,
listed here rather than left implicit.

## Known limitations / deliberate scope choices

- **The access token lives in memory (plus a mirror in
  `sessionStorage` purely to survive a page refresh), not
  `localStorage`.** A JWT in `localStorage` is readable by any script
  that runs on the page — one XSS bug anywhere, including in a
  dependency, is enough to steal it. The tradeoff: refreshing the tab
  requires re-fetching `/auth/me` with the stored token (handled
  automatically in `AuthContext`), and there's currently no
  refresh-token flow on the backend, so a session is only ever as long
  as the 15-minute access token — see the backend README's security
  notes.
- **No global request cache.** Navigating between pages re-fetches.
  Fine at this scale; would need addressing (TanStack Query or
  similar) if the app grew.
- **Types are hand-mirrored from the backend's Pydantic schemas**, not
  generated. Reasonable now; codegen from the OpenAPI schema
  (`openapi-typescript`) is the natural upgrade once the API surface
  stabilizes.
