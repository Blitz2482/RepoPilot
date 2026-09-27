# RepoPilot Implementation Matrix

This matrix maps the v2.0 task registry to the delivered workspace. `Implemented` means the repository contains the requested code/configuration/document. `External` means the task requires credentials, hosted services, a real Bob session, screen capture, or the hackathon submission portal and therefore cannot be truthfully completed inside this offline build environment.

## Phase 0 — Foundation
| Task | Status | Evidence in workspace |
|---|---|---|
| T-10.01 | Implemented | README, CONTEXT_PACK, docs/BUILD_PLAN.md |
| T-10.02 | Implemented | CONTEXT_PACK.md |
| T-10.03 | Implemented | monorepo structure |
| T-10.04 | Implemented | docs/ARCHITECTURE.md, schemas/onboarding_plan.json |
| T-20.01 | Implemented | frontend Next.js 14 scaffold/package.json |
| T-20.02 | Implemented | frontend/app/page.tsx |
| T-20.03 | Implemented | frontend/app/analysis, onboarding routes |
| T-30.01 | External | Bob credentials must be supplied by the event portal |
| T-30.02 | External | Final Bob API contract is external; adapter contract is documented in docs/bob_api.md |
| T-30.03 | External | Live Bob call requires credentials/service access |
| T-30.04 | Implemented | agents.md |
| T-30.05 | Implemented | .bob/rules/onboarding.md |
| T-30.06 | Implemented | backend/bob_client.py |
| T-40.01 | External | Supabase/Postgres instance must be created by deployment owner |
| T-40.02 | Implemented | backend/schema.sql |
| T-40.03 | Implemented | backend/db.py |
| T-40.04 | Implemented | backend/main.py |
| T-50.01 | Implemented | backend/requirements.txt |
| T-50.02 | Implemented | backend/parser.py |
| T-50.03 | Implemented | backend/tests/test_parser.py + deterministic local pipeline test |
| T-60.01 | External | Vercel account/project linking is account-specific |
| T-60.02 | External | Railway account/project linking is account-specific |
| T-60.03 | External | Sentry hosted project/key is account-specific |
| T-60.04 | Implemented | .env.example |
| T-60.05 | Implemented | README.md + .env.example + deployment docs + verification script |

## Phase 1 — Core Pipeline
| Task | Status | Evidence in workspace |
|---|---|---|
| T-11.01 | Implemented | backend/graph.py |
| T-11.02 | Implemented | backend/synthesis.py |
| T-11.03 | Implemented | backend/graph.py asyncio fan-out |
| T-21.01 | Implemented | frontend/app/analysis/[jobId]/page.tsx |
| T-21.02 | Implemented | frontend/hooks/useWebSocket.ts |
| T-31.01 | Implemented | backend/prompts.py |
| T-31.02 | Implemented | backend/bob_client.py |
| T-31.03 | External | Live two-agent validation needs Bob access and public repository network |
| T-41.01 | Implemented | backend/ingest.py |
| T-41.02 | Implemented | backend/routes.py |
| T-41.03 | Implemented | backend/ws.py |
| T-51.01 | Implemented | backend/chunker.py |
| T-51.02 | Implemented | backend/embedder.py |
| T-61.01 | Implemented | backend/Dockerfile, .dockerignore |
| T-61.02 | External | Railway deployment requires account/service secrets |
| T-61.03 | External | Vercel deployment requires account/service secrets |

## Phase 2 — UI + Code Tour
| Task | Status | Evidence in workspace |
|---|---|---|
| T-12.01 | Implemented | backend/synthesis.py generate_tour |
| T-12.02 | Implemented | backend/routes.py /plan + /tour |
| T-12.03 | Implemented | backend/tests + offline end-to-end pipeline check |
| T-22.01 | Implemented | frontend/app/onboarding/[jobId]/page.tsx |
| T-22.02 | Implemented | frontend/components/CodeTourViewer.tsx |
| T-32.01 | Implemented | refined prompts in backend/prompts.py |
| T-32.02 | External | Real Bob session screenshots require live Bob access |
| T-42.01 | Implemented | backend/qa.py |
| T-42.02 | Implemented | backend/routes.py /ask |
| T-52.01 | Implemented | backend/search.py |
| T-52.02 | Implemented | docs/EMBEDDING_QUALITY.md + backend/tests + deterministic retrieval contract |
| T-62.01 | External | Hosted Sentry dashboard creation requires account access |
| T-62.02 | Implemented | backend/monitoring.py |

## Phase 3 — Q&A + Polish
| Task | Status | Evidence in workspace |
|---|---|---|
| T-13.01 | Implemented | backend/synthesis.py build_learning_path |
| T-13.02 | Implemented | graph + integration tests |
| T-23.01 | Implemented | frontend/components/QAPanel.tsx |
| T-23.02 | Implemented | clickable citation pills wired to CodeTourViewer |
| T-33.01 | Implemented | QA_PROMPT in backend/prompts.py |
| T-33.02 | External | Second live repository validation requires network/Bob access |
| T-43.01 | Implemented | validation in qa.py/routes.py + tests |
| T-53.01 | Implemented | vector + Postgres FTS + RRF in backend/search.py/schema.sql |
| T-63.01 | Implemented | backend/tests/test_smoke.py + unit/integration tests |
| T-63.02 | Implemented (offline) | backend/tests/test_three_repo_qa.py covers Python, TypeScript, and mixed repositories; live-provider validation remains deployment-time |

## Phase 4 — Demo + Submit
| Task | Status | Evidence in workspace |
|---|---|---|
| T-14.01 | Implemented | docs/PITCH_DECK.md |
| T-14.02 | Implemented | docs/DEMO_SCRIPT.md |
| T-24.01 | Implemented | final responsive frontend components |
| T-24.02 | External | Screen capture is a human/device action |
| T-34.01 | Implemented | docs/BOB_PLAYBOOK.md |
| T-34.02 | External | Real Bob evidence package requires Bob sessions/screenshots |
| T-44.01 | Implemented | README.md |
| T-54.01 | Implemented | evidence/fallback_demo_plan.json + frontend/public/fallback_demo_plan.json + /demo |
| T-64.01 | External | Final video recording is a human/device action |
| T-64.02 | External | Submission portal action requires the team's account |

## Verification performed in this environment
- Backend Python imports: passed.
- Backend compileall: passed.
- Pytest: **42 passed, 1 skipped** (the skipped test is the live GitHub end-to-end case).
- Deterministic local full pipeline: **done, 100% progress, exactly 8 tour steps**.
- FastAPI `/health`: **200 OK**.
- FastAPI `/metrics`: **200 OK**.
- Frontend deployment configuration: PASS.
- Frontend dependencies were not installable in the sandbox because the external npm registry was unavailable, so a full `next build` could not be executed locally; the CI workflow is configured to install and build the frontend on GitHub Actions.
- Local deployment-contract verification using the live FastAPI server, mock Bob, and a controlled Git fixture passed `/health`, `/ready`, `/openapi.json`, `/metrics`, repository submission, completion, all 8 source citations, grounded Q&A citations, and WebSocket snapshot/complete.
