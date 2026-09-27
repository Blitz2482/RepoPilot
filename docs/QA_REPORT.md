# RepoPilot QA Report

## Automated checks

The repository has been verified with the following checks in the build environment:

- Python compile check: `python -m compileall -q backend scripts` — PASS.
- Backend test suite: `pytest -q backend` — **42 passed, 1 skipped**.
- Deployment structure verification: `python scripts/verify_deployment.py` — PASS.
- Frontend deployment configuration verification: `node scripts/verify_frontend_config.mjs` — PASS.
- Deterministic full-pipeline integration: PASS; final status `done`, progress `100`, exactly 8 tour steps.
- WebSocket snapshot contract: PASS.
- Redis idle-poll regression: PASS; an idle pub/sub poll is not treated as an outage.
- Production HTTPS configuration guards: PASS for frontend API URL and Bob base URL.
- Persistence recovery tests: PASS for restoring completed plans and reporting interrupted jobs after process restart.
- Path/line-range hardening tests: PASS.
- Production CORS safety validation: PASS.
- Local deployment-contract verification using the live FastAPI server with controlled Git and mock Bob: PASS; `/health`, `/ready`, `/openapi.json`, `/metrics`, submit, completion, eight source citations, Q&A citation resolution, and WebSocket snapshot/complete all passed.

The one skipped test is the live GitHub end-to-end case and remains disabled unless `RUN_SLOW=1` because it requires external network/service access.

## Deployment artifact checks

- Production Dockerfile uses Python 3.11 slim, installs Git/CA certificates and PostgreSQL runtime support, runs as a non-root user, exposes port 8000, and declares a `/health` container healthcheck.
- Railway deployment settings are documented in `.railway/README.md` and `docs/RAILWAY_SETTINGS.json`; the service uses repository-root Docker context with `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`, and no deprecated `railway.json` is shipped.
- Vercel configuration targets Next.js and the frontend expects `NEXT_PUBLIC_API_URL` during production builds.
- Credential placeholders are left empty by design.

## Manual/live checks still required at deployment time

- Confirm the actual IBM Bob endpoint/authentication/request schema supplied by the hackathon portal.
- Supply `DATABASE_URL` and apply `backend/schema.sql` to PostgreSQL/Supabase with pgvector enabled.
- Supply optional Redis/Sentry credentials if those services are used.
- Configure the Vercel and Railway projects and their production environment variables.
- Run `python scripts/verify_live_deployment.py https://<backend> --repo https://github.com/owner/repo` after the services are deployed, then follow the production verification sequence in `docs/DEPLOYMENT.md`.
- Capture real Bob session evidence under `evidence/bob_sessions/` and perform the human demo/submission actions.

## Acceptance conditions

A deployment is considered operational only when `/health` is 200, `/ready` is 200, the repository submission returns a job ID, the WebSocket reaches `complete`, the plan contains exactly 8 tour steps, source citations load, and `/ask` returns only citations that belong to retrieved repository chunks.


## Release gate

The consolidated `python scripts/release_verify.py` gate also passes. It reruns backend compilation, deployment-structure checks, frontend configuration/syntax checks, and the complete backend test suite. The only intentionally skipped item is the live GitHub/provider smoke test.

- Offline three-repository QA coverage: PASS for Python, TypeScript, and mixed repository fixtures; this does not substitute for live-provider validation.
- Embedding quality contract report: PASS and documented in `docs/EMBEDDING_QUALITY.md`; hosted-provider semantic accuracy remains deployment-time.
