# Smorx Web — Phase 0 Health Path

Minimal Next.js app for Phase 0 of the Software Evolution Intelligence System (Nebius x NVIDIA Global AI Hackathon, Track 1).

**Purpose:** verify that the browser → Next.js (localhost:3000) → `/api/health` proxy → FastAPI backend (127.0.0.1:8000) → `GET /health` path works end to end, showing the real backend response.

## How to run

1. Start the FastAPI backend (from repo root) on 127.0.0.1:8000:

   ```bash
   python -m uvicorn app.main:create_app --app-dir apps/api
   ```

2. Start the web app:

   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

3. Open http://localhost:3000 .

## What the page shows

- The backend `status` from `GET /health` (`{"status":"ok"}`)
- Whether the fetch succeeded
- An explicit `PHASE 0 HEALTH PATH: OK / FAILED` line driven by the real response
- The raw JSON response
- A timestamp (and the error text if the request fails)

## Configuration

`API_BASE_URL` (see `.env.example`) points at the FastAPI backend. It defaults to `http://127.0.0.1:8000`. The Next.js dev/server proxy keeps requests same-origin so no backend CORS change is needed.

## Scope note

This is deliberately the Phase 0 minimum — a single health page with no design system or Tailwind wiring. The full persistent application shell (one system, eight journey tabs) arrives in Phase 5.