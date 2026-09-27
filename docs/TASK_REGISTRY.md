> **Registry note:** The Bundle v2.0 cover states “55 tasks,” but Chapters 27.1–27.5 enumerate **74 unique Task IDs**. This implementation follows the actual registry tables and tracks all 74 IDs rather than silently reconciling the source discrepancy.

# Complete RepoPilot Task Registry (implementation map)

## Phase 0 — Foundation (0–6h)
| Task | Owner | Deliverable / implementation | Depends |
|---|---|---|---|
| T-10.01 | Dev 1 | Playbook alignment | — |
| T-10.02 | Dev 1 | CONTEXT_PACK.md | T-10.01 |
| T-10.03 | Dev 1 | Monorepo | T-10.01 |
| T-10.04 | Dev 1 | Architecture/schema docs | T-10.03 |
| T-20.01 | Dev 2 | Next.js scaffold | T-10.03 |
| T-20.02 | Dev 2 | Submit screen | T-20.01 |
| T-20.03 | Dev 2 | Routes skeleton | T-20.01 |
| T-30.01 | Dev 3 | Bob credentials | — |
| T-30.02 | Dev 3 | Bob API spec | T-30.01 |
| T-30.03 | Dev 3 | First Bob call proof | T-30.02 |
| T-30.04 | Dev 3 | agents.md | T-30.02 |
| T-30.05 | Dev 3 | .bob/rules/onboarding.md | T-30.02 |
| T-30.06 | Dev 3 | bob_client.py v1 | T-30.03 |
| T-40.01 | Dev 4 | Supabase/DB instance | T-10.03 |
| T-40.02 | Dev 4 | schema.sql | T-40.01 |
| T-40.03 | Dev 4 | db.py | T-40.02 |
| T-40.04 | Dev 4 | main.py skeleton | T-10.03 |
| T-50.01 | Dev 5 | Tree-sitter deps | T-10.03 |
| T-50.02 | Dev 5 | parser.py v1 | T-50.01 |
| T-50.03 | Dev 5 | Parser evidence | T-50.02 |
| T-60.01 | Dev 6 | Vercel linked | T-10.03 |
| T-60.02 | Dev 6 | Railway linked | T-10.03 |
| T-60.03 | Dev 6 | Sentry live | T-10.03 |
| T-60.04 | Dev 6 | .env.example | T-30.02, T-40.01 |
| T-60.05 | Dev 6 | README.md | T-10.04 |

## Phase 1 — Core Pipeline (6–12h)
| Task | Owner | Deliverable / implementation | Depends |
|---|---|---|---|
| T-11.01 | Dev 1 | graph.py | T-30.06, T-40.04, T-50.02 |
| T-11.02 | Dev 1 | synthesis.py | T-11.01 |
| T-11.03 | Dev 1 | Bob fanout | T-11.01, T-30.06 |
| T-21.01 | Dev 2 | Live analysis page | T-20.03, T-10.04 |
| T-21.02 | Dev 2 | useWebSocket hook | T-21.01 |
| T-31.01 | Dev 3 | prompts.py v1 | T-30.04, T-30.05 |
| T-31.02 | Dev 3 | bob_client.py v2 | T-30.06, T-31.01 |
| T-31.03 | Dev 3 | Two-agent validation | T-31.02 |
| T-41.01 | Dev 4 | ingest.py | T-40.03 |
| T-41.02 | Dev 4 | routes.py | T-40.04 |
| T-41.03 | Dev 4 | ws.py | T-41.02 |
| T-51.01 | Dev 5 | chunker.py | T-50.02 |
| T-51.02 | Dev 5 | embedder.py | T-51.01, T-40.03 |
| T-61.01 | Dev 6 | Dockerfile | T-40.04 |
| T-61.02 | Dev 6 | Railway backend deploy | T-61.01 |
| T-61.03 | Dev 6 | Vercel frontend deploy | T-20.03 |

## Phase 2 — UI + Code Tour (12–24h)
| Task | Owner | Deliverable / implementation | Depends |
|---|---|---|---|
| T-12.01 | Dev 1 | Tour generator | T-11.02 |
| T-12.02 | Dev 1 | /plan + /tour | T-11.03 |
| T-12.03 | Dev 1 | Midpoint integration test | T-12.02, T-22.01 |
| T-22.01 | Dev 2 | Dashboard | T-21.02 |
| T-22.02 | Dev 2 | CodeTourViewer | T-22.01 |
| T-32.01 | Dev 3 | Refined prompts | T-31.03 |
| T-32.02 | Dev 3 | Bob session evidence | T-31.03 |
| T-42.01 | Dev 4 | qa.py | T-51.02 |
| T-42.02 | Dev 4 | /ask | T-42.01 |
| T-52.01 | Dev 5 | search.py | T-51.02 |
| T-52.02 | Dev 5 | Embedding quality report | T-51.02 |
| T-62.01 | Dev 6 | Sentry dashboards | T-60.03 |
| T-62.02 | Dev 6 | Request ID middleware | T-40.04 |

## Phase 3 — Q&A + Polish (24–36h)
| Task | Owner | Deliverable / implementation | Depends |
|---|---|---|---|
| T-13.01 | Dev 1 | Learning path | T-12.01 |
| T-13.02 | Dev 1 | Full integration | T-12.03, T-22.02, T-42.02 |
| T-23.01 | Dev 2 | QAPanel | T-22.02 |
| T-23.02 | Dev 2 | Clickable citations | T-23.01 |
| T-33.01 | Dev 3 | QA retrieval prompt | T-32.01 |
| T-33.02 | Dev 3 | Second-repo validation | T-33.01 |
| T-43.01 | Dev 4 | /ask edge cases | T-42.02 |
| T-53.01 | Dev 5 | Hybrid search/RRF/FTS | T-52.01 |
| T-63.01 | Dev 6 | Smoke tests | All P2 |
| T-63.02 | Dev 6 | QA report on 3 repos | T-63.01 |

## Phase 4 — Demo + Submit (36–48h)
| Task | Owner | Deliverable / implementation | Depends |
|---|---|---|---|
| T-14.01 | Dev 1 | Pitch deck | T-13.02 |
| T-14.02 | Dev 1 | Demo rehearsal | T-14.01 |
| T-24.01 | Dev 2 | Final UI polish | T-23.02 |
| T-24.02 | Dev 2 | Screen capture | T-24.01 |
| T-34.01 | Dev 3 | Final BOB_PLAYBOOK.md | T-33.02 |
| T-34.02 | Dev 3 | Bob evidence zip | T-32.02 |
| T-44.01 | Dev 4 | Final README | T-13.02 |
| T-54.01 | Dev 5 | Fallback demo data | T-13.02 |
| T-64.01 | Dev 6 | Final demo video | T-24.02, T-14.02 |
| T-64.02 | Dev 6 | Submission | DEL-09, T-34.01, T-44.01 |

## Gate checklist
- G-06: foundation complete
- G-12: pipeline end-to-end
- G-18: first end-to-end attempt
- G-24: UI + tour visible
- G-30: integration freeze
- G-36: QA green
- G-40: demo recorded
- G-46: submission complete
