# 48-hour build registry and gates

The source bundle defines five phases and eight gates. This implementation maps the registry to concrete repository files.

## Phase 0 — Foundation (0–6h)
- T-10.02 -> `CONTEXT_PACK.md`
- T-10.04 -> `docs/ARCHITECTURE.md`, schemas
- T-20.01/T-20.02/T-20.03 -> Next.js scaffold + submit/routing screens
- T-30.04/T-30.05 -> `agents.md`, `.bob/rules/onboarding.md`
- T-30.06 -> `backend/bob_client.py`
- T-40.02/T-40.03/T-40.04 -> `backend/schema.sql`, `db.py`, `main.py`
- T-50.02 -> `backend/parser.py`
- T-60.04/T-60.05 -> `.env.example`, `README.md`

## Phase 1 — Core Pipeline (6–12h)
- T-11.01/T-11.02/T-11.03 -> `graph.py`, `synthesis.py`, Bob fanout
- T-21.01/T-21.02 -> live analysis page + WebSocket hook
- T-31.01/T-31.02 -> `prompts.py` + Bob client hardening
- T-41.01/T-41.02/T-41.03 -> ingestion/routes/WebSocket
- T-51.01/T-51.02 -> chunking/embeddings
- T-61.01 -> backend Dockerfile

## Phase 2 — UI + Code Tour (12–24h)
- T-12.01/T-12.02 -> eight-step tour + plan/tour endpoints
- T-22.01/T-22.02 -> dashboard + viewer
- T-32.01 -> refined prompts
- T-42.01/T-42.02 -> Q&A pipeline
- T-52.01/T-52.02 -> search and retrieval quality
- T-62.01/T-62.02 -> monitoring and request IDs

## Phase 3 — Q&A + Polish (24–36h)
- T-13.01/T-13.02 -> learning path and full integration
- T-23.01/T-23.02 -> Q&A panel + citations
- T-33.01/T-33.02 -> grounded retrieval prompt and validation
- T-43.01 -> QA edge cases
- T-53.01 -> hybrid retrieval / RRF / FTS
- T-63.01/T-63.02 -> tests

## Phase 4 — Demo + Submit (36–48h)
- T-14.01/T-14.02 -> pitch deck + rehearsal
- T-24.01/T-24.02 -> final UI polish/capture
- T-34.01/T-34.02 -> Bob playbook + evidence bundle
- T-44.01 -> final README
- T-54.01 -> fallback demo data
- T-64.01/T-64.02 -> final demo + submission

## Gates
G-06 foundation, G-12 pipeline, G-18 first end-to-end, G-24 UI + tour, G-30 integration freeze, G-36 QA green, G-40 demo recorded, G-46 submission complete.
