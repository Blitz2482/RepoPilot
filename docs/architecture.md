# RepoPilot Architecture

RepoPilot implements the bundle's six-stage flow:

1. **Ingest** — validate GitHub URL, shallow clone, detect metadata.
2. **Parse** — Tree-sitter extracts structural code symbols.
3. **Embed** — AST-aligned chunks are persisted with 1536-dimensional embeddings.
4. **Spawn** — Architecture and Business Logic Bob agents run concurrently.
5. **Synthesize** — findings become an exactly-eight-step evidence-backed onboarding plan.
6. **Emit** — plan is persisted and live progress is published over WebSocket.

Frontend: Next.js 14 App Router + Tailwind + shadcn-style primitives.
Backend: FastAPI + Pydantic 2 + LangGraph.
Persistence: PostgreSQL + pgvector.
Monitoring: Sentry hooks + structured logging + request IDs + `/metrics`.
Deployment: Vercel frontend and Railway backend.
