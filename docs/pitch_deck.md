# RepoPilot — 10-slide pitch deck content

## Slide 1 — RepoPilot
- Turn a codebase into a guided tour.
- Evidence-backed architecture, code tour, and Q&A.
- Built around full-repository agentic analysis.

## Slide 2 — The problem
- Healthy onboarding can still take 2–3 weeks.
- The supplied bundle cites ~80 engineer-hours of team effort per new hire.
- READMEs, search, and visualizations each solve only part of the understanding problem.

## Slide 3 — The solution
- Submit a GitHub URL and role.
- Watch two specialized agents analyze the repository.
- Receive architecture, 8-step code tour, and grounded Q&A.

## Slide 4 — Live demo
- Real public repository input.
- Live Architecture + Business Logic cards.
- Evidence-linked code-tour steps.

## Slide 5 — How it works
- Ingest -> Parse -> Embed -> Spawn -> Synthesize -> Emit.
- Tree-sitter creates structural evidence.
- LangGraph coordinates stateful analysis.

## Slide 6 — IBM Bob 2.0 usage
- Agent Mode as the runtime analysis engine.
- Two parallel specialized subagents.
- Custom `agents.md` and `.bob/rules/onboarding.md`.
- Evidence captured for the submission.

## Slide 7 — Architecture
- Next.js frontend.
- FastAPI backend.
- LangGraph orchestrator.
- PostgreSQL + pgvector.
- Bob primary, GPT-4o fallback.

## Slide 8 — Scalability
- Stateless API boundaries around jobs.
- Shallow repository ingestion keeps the MVP bounded.
- Hybrid retrieval combines semantic and keyword signals.

## Slide 9 — Team
- Lead / Orchestrator.
- Frontend.
- Bob integration.
- Backend.
- Code intelligence.
- DevOps / QA.

## Slide 10 — Close
- RepoPilot turns source code into a guided onboarding experience.
- The developer starts with a map, not a maze.
