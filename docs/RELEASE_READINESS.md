# RepoPilot Release Readiness

This document records the non-credential deployment-readiness work performed against the supplied RepoPilot Bundle v2.0.

## Step 1 — Source alignment

Verified against the supplied bundle:

- MVP: GitHub repository ingestion, two Bob analysis agents, eight-step code tour, architecture dashboard, and grounded Q&A.
- Tech stack: Next.js 14, FastAPI/Python 3.11, LangGraph, Tree-sitter, PostgreSQL + pgvector, Bob primary, GPT fallback, Vercel frontend, Railway backend.
- Public API: repository submit/status/plan/tour/ask plus WebSocket stream.
- Bob context contract: `agents.md` and `.bob/rules/onboarding.md` are shipped.

## Step 2 — Backend correctness

Verified:

- Python compilation passes.
- LangGraph-compatible six-stage pipeline is present: ingest -> parse -> embed -> fanout -> synthesize -> emit.
- Graph nodes have two retries and a 120-second node timeout.
- Overall pipeline has a five-minute timeout guard.
- Bob Architecture and Business Logic calls run concurrently.
- Partial agent failure is tolerated; complete agent failure fails the job.
- Tour generation produces exactly eight ordered steps and rejects fabricated source paths.
- Source citations are bounded to real analyzed files and real line ranges.
- Repository cloning validates GitHub URLs, uses shallow clones, supports optional token injection, and enforces size/time limits.
- Q&A validates question length and filters citations to retrieved repository chunks.
- Completed plans persist to PostgreSQL and can be restored after process restart.
- Stale cleanup does not remove active jobs.
- Logging is safe for both HTTP request logs and background/child logger records.

## Step 3 — Frontend correctness

Verified:

- Submit screen validates GitHub URL and supported roles.
- Live analysis uses WebSocket progress and stops reconnecting after terminal events.
- Onboarding dashboard has architecture, code tour, and grounded Q&A sections.
- Code tour supports previous/next navigation and `j`/`k` shortcuts.
- Q&A citation buttons map back to a relevant tour step.
- Production frontend builds require `NEXT_PUBLIC_API_URL` and require HTTPS.
- Next.js security headers disable the powered-by header and add HSTS, anti-clickjacking, content-type and referrer policies.
- All TypeScript/TSX source files pass syntax parsing.

## Step 4 — Deployment configuration

Verified:

- Backend Dockerfile uses Python 3.11 slim, Git/CA certificates/PostgreSQL runtime support, a non-root user, port 8000, `/health` healthcheck, and Railway `$PORT` handling.
- Docker build context is the repository root; `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile` is documented in the Railway deployment settings reference.
- No real `.env` or frontend local environment file is included.
- Frontend Vercel configuration targets Next.js and uses `frontend/` as the deployment root.
- CI installs backend/frontend dependencies and runs backend tests, frontend typecheck and frontend build.
- `AGENTS.md` mirrors `agents.md` for compatibility with current Bob project-context tooling.

## Step 5 — Verification results

Latest local results:

```text
Backend tests:                 42 passed, 1 skipped
Frontend syntax parser:        PASS (22 TypeScript/TSX files)
Frontend config verification:  PASS
Deployment structure check:    PASS
Backend compile check:         PASS
Local HTTP E2E (mock mode):    PASS
Local full pipeline:           PASS
Production /ready gate:        PASS when dependency contract is satisfied by test doubles
```

The single skipped backend test is the deliberately disabled live GitHub test. It requires external network/service access.

## Step 6 — External deployment inputs still required

These are intentionally not fabricated:

1. IBM Bob credentials and the final Bob API/request specification supplied by the hackathon.
2. A real Supabase/PostgreSQL + pgvector instance and `DATABASE_URL`.
3. OpenAI fallback/embedding credentials.
4. Optional GitHub token for private repositories.
5. Optional Redis and Sentry credentials/services.
6. The Vercel and Railway account/project linkage and production domains.
7. A real Bob session/evidence capture and hackathon portal submission.

## Go/no-go interpretation

The repository is **code/deployment-package ready** for the non-credential portion of the supplied MVP. It is not a claim of a live hosted deployment until the external inputs above are supplied and `scripts/verify_live_deployment.py` passes against the real Railway service.

## Final hardening pass

The final verification pass also confirms that the emit/persistence stage participates in the same two-retry/120-second node contract as the other graph stages, and the frontend avoids sending a non-safelisted JSON Content-Type header on GET requests.

- Three-repository offline QA: PASS (Python, TypeScript, and mixed fixtures), with live-provider verification intentionally remaining deployment-time.

- Repository documentation hardening: README files are included as document context for chunking/Q&A and as deterministic tour anchors without being passed through Tree-sitter.

- API hardening: public job snapshots no longer expose internal clone filesystem paths, and pipeline failures expose exception type rather than raw provider/path error strings.
