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

## Status

Implementation proceeds phase-by-phase per plan.md Section 25. See plan.md Section 33 for the
current status.
