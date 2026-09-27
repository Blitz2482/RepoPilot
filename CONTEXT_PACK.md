# RepoPilot AI Context Pack v1.0

## What We Are Building
RepoPilot Onboarding: an agentic AI platform that ingests a GitHub repository and autonomously generates a personalized onboarding experience (architecture summary, code tour, grounded Q&A).

## Team Constraints
- 6 developers, 48 hours, limited deep expertise
- Must use IBM Bob 2.0 as the code analysis engine
- MVP scope: 1 repo, 2 subagents, 8-step tour, basic Q&A

## Tech Stack (DO NOT DEVIATE)
- Frontend: Next.js 14 (App Router), Tailwind, shadcn/ui
- Backend: FastAPI (Python 3.11+), Pydantic v2
- Orchestration: LangGraph
- Code parsing: Tree-sitter (Python, TypeScript, JavaScript only)
- Database: PostgreSQL + pgvector (via Supabase)
- LLM: IBM Bob 2.0 (primary), GPT-4o (fallback)
- Deployment: Vercel (FE), Railway (BE)

## Core Data Schemas (Use These Exactly)
RepoContext: repo_url, default_branch, languages, file_count
AgentFinding: agent, summary, evidence, confidence
OnboardingPlan: role, tour_steps (8), architecture_summary, key_concepts

## Rules for AI Responses
1. Always return COMPLETE, RUNNABLE code no placeholders
2. Include all imports
3. Include error handling
4. Add inline comments explaining non-obvious logic
5. If a library is needed, state the exact pip/npm install
6. Assume the developer is a junior explain any magic

## What NOT To Do
- Do NOT suggest new libraries without justification
- Do NOT change the data schemas
- Do NOT suggest Docker, Kubernetes, or complex infra
- Do NOT write tests unless explicitly asked

## RepoPilot implementation notes
- The public API contract is documented in docs/API.md.
- Bob's exact production API specification was not included in the source bundle; backend/bob_client.py therefore implements the bundle's starter `/agent/run` contract behind configurable BOB_BASE_URL and BOB_ENDPOINT settings and supports a mock provider for local/demo execution.
- Production persistence uses PostgreSQL + pgvector. Local development can run in memory with DEV_MODE=true.

## Current Task
Build the complete RepoPilot repository from the bundle specification.
