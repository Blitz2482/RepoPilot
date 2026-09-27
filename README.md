# RepoPilot Onboarding

RepoPilot is an agentic repository onboarding platform that accepts a GitHub URL and role, analyzes the repository with a six-stage LangGraph pipeline, and presents an evidence-backed 8-step code tour plus grounded Q&A.

The implementation follows the supplied RepoPilot Complete Bundle v2.0: Next.js 14/Tailwind UI, FastAPI/Pydantic backend, LangGraph orchestration, Tree-sitter parsing, PostgreSQL + pgvector, IBM Bob 2.0 as the primary analysis engine, and a GPT fallback.

## Repository structure

```text
repopilot/
├── .bob/rules/onboarding.md
├── CONTEXT_PACK.md
├── AGENTS.md / agents.md
├── schemas/onboarding_plan.json
├── backend/
│   ├── main.py routes.py ws.py graph.py
│   ├── bob_client.py prompts.py synthesis.py
│   ├── ingest.py parser.py chunker.py embedder.py search.py qa.py
│   ├── db.py schema.sql monitoring.py job_store.py models.py config.py
│   ├── Dockerfile .dockerignore requirements.txt
│   └── tests/
├── frontend/
│   ├── app/page.tsx
│   ├── app/analysis/[jobId]/page.tsx
│   ├── app/onboarding/[jobId]/page.tsx
│   ├── app/demo/page.tsx
│   ├── components/CodeTourViewer.tsx QAPanel.tsx ui/*
│   └── hooks/useWebSocket.ts lib/*
├── docs/ (API, architecture, Bob playbook, pitch deck, demo script, QA)
└── evidence/fallback_demo_plan.json + bob_sessions/
```

## Local setup

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd ..
copy .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

For a no-credentials local demo, keep `DEV_MODE=true`, `MOCK_BOB=true`, and `LOCAL_EMBEDDINGS=true`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Production configuration

Set `DATABASE_URL` to a PostgreSQL database with the pgvector extension enabled. Set `BOB_API_KEY`, `BOB_BASE_URL`, and `BOB_ENDPOINT` to the actual IBM Bob credentials/API specified by the hackathon portal. The supplied PDF contains the starter `/agent/run` contract but not the event's final external API specification.

Set `OPENAI_API_KEY` for GPT-4o fallback and OpenAI embeddings when `LOCAL_EMBEDDINGS=false`. Set `GITHUB_TOKEN` only when authenticated repositories are required, and then set `ALLOW_PRIVATE_REPOS=true`. Keep it `false` for public-only deployments.

## Database

Apply `backend/schema.sql` to PostgreSQL/Supabase before live usage. It includes the core tables from the bundle plus the `code_chunks_fts` tsvector column required for hybrid search.

## Tests

```bash
cd backend
pytest -q
```

The live GitHub end-to-end smoke test is intentionally marked slow and runs only with `RUN_SLOW=1`.

## Deployment

- Frontend: Vercel, rooted at `frontend/`.
- Backend: Railway, using the repository root as build context and `backend/Dockerfile` via `RAILWAY_DOCKERFILE_PATH`.
- Railway settings: `.railway/README.md` and `docs/RAILWAY_SETTINGS.json`.
- Required variables are listed in `.env.example`; credential values are intentionally omitted.
- Run `python scripts/verify_deployment.py` before publishing a release.
- Run `python scripts/release_verify.py` for the full local release gate.
- See `docs/RELEASE_READINESS.md` for the latest verification status.
- Run the backend test suite with `pytest -q backend`.

The codebase is deployment-hardened for the non-credential portions of the supplied MVP. `AGENTS.md` mirrors the bundle's `agents.md` contract so current Bob tooling that looks for an `AGENTS.md` project context file can use the same instructions without changing the bundle artifact. Live Bob access, hosted Postgres/pgvector, optional Redis/Sentry, and Vercel/Railway account configuration remain deployment-time dependencies.

## Important external dependency

The provided bundle tells the team to obtain the real Bob API documentation from the hackathon portal, but that external document was not embedded in the PDF. `backend/bob_client.py` keeps Bob behind a small adapter so replacing the endpoint/request shape is localized.
