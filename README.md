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
