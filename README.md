# ASBO — Autonomous Scheme-Bundle Optimizer for Citizens

See [plan.md](plan.md) for the full specification (requirements, data model, API design, phased build plan).

## Prerequisites

- Python 3.11+ (developed against 3.14)
- Node.js 20+
- MongoDB running locally (default: `mongodb://localhost:27017`) or via Docker:
  `docker run -d -p 27017:27017 --name asbo-mongo mongo:7`

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env       # then fill in MONGO_URI/GEMINI_API_KEY as needed
```

Then, any time, from `backend/`:

```bash
npm run dev
```

(`backend/package.json` is just a thin wrapper around uvicorn, so both backend and frontend
start the same way regardless of which shell you're in.)

Health check: `GET http://localhost:8000/health`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173` and calls the backend at `http://localhost:8000` by default
(override with a `VITE_API_BASE_URL` env var).

## Mobile app

React Native (Expo) app in `mobile/` covering the same citizen journey as the web frontend:
onboarding, personalized dashboard (eligible schemes + optimized bundle), and an explore tab
for searching/filtering the full scheme catalogue. Runs in Expo Go — no native build needed.

```bash
cd mobile
npm install
npx expo start --lan
```

Scan the QR code with the Expo Go app (same Wi-Fi network as this machine). The API base URL
is auto-detected from the Metro dev server's host at runtime, so it talks to the backend on
`:8000` on this machine without any config — override with an `EXPO_PUBLIC_API_BASE_URL` env
var if needed (e.g. a backend on a different host).

## RAG layer (policy knowledge base)

Beyond the curated `schemes` collection above, `gov_schemes_cleaned.json` (repo root —
3,397 real scheme records, produced by `clean_gov_schemes.py`) is indexed into a local Chroma
vector store + BM25 keyword index for retrieval-grounded answers (scheme discovery, deadline
lookup, grievance department lookup, document requirement checks). Build/refresh the index:

```bash
cd backend && source .venv/bin/activate   # or the Windows equivalent
python scripts/ingest_policies.py
```

Requires a real `GEMINI_API_KEY` in `backend/.env` (embeddings are not optional for RAG,
unlike the Explanation Agent's optional LLM call) and writes to `backend/data/chroma/` +
`backend/data/bm25_index.pkl` (gitignored — rebuild locally rather than committing). The
free Gemini API tier's embedding quota is fairly low (100 requests/minute at the time of
writing); ingesting the full 3,397-scheme corpus in one run may need to pause/retry against
that limit, or you can point `POLICY_CORPUS_PATH` at a smaller slice of the file for a quick
local smoke test.

Try it once ingested: `GET /api/policy/search?q=farmer%20income%20support`, or with the
backend running against no real key at all, every RAG-backed endpoint still degrades
honestly (an empty/`"verified": false` result) rather than failing — see
`app/rag/policy_service.py`'s module docstring.

## New agents (Document Verification, Deadline/Reminder, Feedback/Grievance, Fraud
Detection, Multi-language Chat)

Each follows the same `modules/<name>/{engine.py, service.py}` + `api/<name>.py` pattern as
the original 8 agents (see plan.md Section 11), and each is additive — none of the original
`/api/citizens`, `/api/schemes`, `/api/eligibility`, `/api/conflicts`, `/api/bundle`,
`/api/checklist`, `/api/agent` endpoints changed behavior. New surfaces:

- `POST /api/documents/verify` — structural checks only (text-layer PDF parsing via `pypdf`,
  no OCR); `authenticity_verified` is always `false`.
- `POST /api/reminders` (requires `consent: true`) / `GET /api/reminders/{citizen_id}` —
  `notification_sent` is always `false` (no real SMS/email provider is configured).
- `POST /api/grievances` / `GET /api/grievances/citizen/{citizen_id}` — `is_official_submission`
  is always `false` (internal platform ticket only).
- `POST /api/fraud/screen` — deterministic risk indicators + `human_review_required`; never a
  "confirmed fraud" verdict.
- `POST /api/language/detect-translate`, `POST /api/language/translate-response`.
- `POST /api/assistant/message` / `POST /api/assistant/message/resume` — the LangGraph entry
  point that intent-routes a free-text message across all 13 agents, including the
  human-review interrupt/resume cycle for document verification and fraud screening
  (`app/graph/workflow.py`).

## Context-Aware Form Assistance (browser extension + mobile toggle)

A browser extension and a mobile in-app WebView screen that explain a confusing scheme
application form question in plain language (text + voice, and now text-selection **or** a
cropped screenshot) — but **only** on a page reached through this platform's own verified
"Apply Now" link, never as a general-purpose assistant on arbitrary websites. See
`extension/README.md` for the full design (session handshake, why it needs the `<all_urls>`
host permission but never uses it outside a session-marked page, privacy notes, and
honestly-listed limitations — RAG grounding depends on the vector store actually being built).

## Maharashtra representative seed set (A-011)

`database/seed_schemes_maharashtra.json` — 5 real, named Maharashtra/MahaDBT-aligned schemes
(MahaDBT EBC tuition waiver, Dr. Punjabrao Deshmukh hostel allowance, Namo Shetkari top-up,
Sanjay Gandhi Niradhar Anudan pension, Ramai Awas Gharkul housing), each with `links` populated
by directly fetching the official domain rather than trusting a search snippet (see the file's
own `verification_notes` per scheme). Deliberately a *second*, separate seed file from
`database/seed_schemes.json` — not merged, and not loaded automatically on startup:

```bash
cd backend && ./.venv/Scripts/python.exe scripts/seed_maharashtra.py   # or the Unix venv path
```

Safe to re-run — inserts only schemes not already present by name. PM-KISAN is intentionally
*not* repeated here even though it was part of the original six-scheme concept, since it's
already in `seed_schemes.json`. Ramai Awas Gharkul shares the `housing_subsidy` conflict group
with `seed_schemes.json`'s own PMAY-Rural/State Rural Housing Assistance pair — conflict groups
are just a shared string, not scoped to one file, so once both files are loaded a citizen
eligible for schemes from both sets still gets a correctly resolved, non-overlapping bundle
(verified live against a real MongoDB Atlas cluster, not just the test suite).

Load it: `chrome://extensions` → enable Developer mode → Load unpacked → select `extension/`.
The mobile counterpart (`mobile/src/screens/ApplicationWebViewScreen.js`) opens applications in
an in-app WebView with the same session handshake, since a phone's external system browser
can't be read/controlled by the app at all.

New backend surface: `POST /api/assistance/session`, `/validate-session`, `/explain-text`,
`/feedback`, `GET /api/assistance/languages` (`app/api/assistance.py`), backed by a dedicated
LangGraph workflow (`app/graph/form_assistance_workflow.py`) that reuses the existing RAG
(`app/rag/policy_service.py`) and Multi-language Chat Agent services rather than
reimplementing them.

Each scheme's `links` (see `SchemeLinks` in `app/models/scheme.py`) now separately tracks a
policy page, official homepage, application form, renewal portal, and grievance portal — never
one conflated URL — plus an `application_link_status` (`verified` / `unverified` /
`not_available` / `state_specific`) and verification notes, so the UI never presents an
unverified or nonexistent online application as if it were official.

## Database

- `database/seed_schemes.json` — sample scheme knowledge base (loaded into MongoDB on backend
  startup when `SEED_SCHEMES_ON_STARTUP=true`).
- `database/init_indexes.js` — compound indexes per plan.md Section 13. Run with:
  `mongosh <connection-string> database/init_indexes.js`

## Testing

Backend (pytest, isolated mongomock database — no real MongoDB needed):

```bash
backend/.venv/Scripts/python.exe -m pytest   # run from the repo root
```

Frontend E2E (Playwright, drives the full citizen journey through a real browser):

```bash
npm install                     # once, at the repo root — installs @playwright/test
npx playwright install chromium # once
cd frontend && npm run build && npm run preview -- --port 4173   # in one terminal
# with the backend also running on :8000 and MongoDB reachable:
npx playwright test             # from the repo root, in another terminal
```

The E2E test targets the production preview build (port 4173) rather than the dev server by
default, since React StrictMode's dev-only double-effect-invocation would otherwise double
every write the journey makes. Override with `E2E_BASE_URL=http://localhost:5173` to run
against the dev server instead.

`admin.spec.js` logs in as a real admin account via the backend API directly (register →
login → verify-otp), not through the UI, since the UI login needs a real OTP email — this only
works if `backend/.env`'s `RESEND_API_KEY` is **unset** when running the suite (falling back to
`debug_otp`, see `app/core/email_sender.py`); with a real key configured, that test fails with a
clear message explaining why rather than hanging.

## Status

Implementation proceeds phase-by-phase per plan.md Section 25. See plan.md Section 33 for the
current status.
