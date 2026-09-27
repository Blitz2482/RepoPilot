# RepoPilot — BOB_PLAYBOOK.md

## 1. Overview: how RepoPilot uses Bob Agent Mode

RepoPilot's runtime analysis engine is designed around IBM Bob 2.0 Agent Mode and full-repository context. The orchestration sends two independent investigations in parallel:

- **ArchitectureAgent:** module map, entry points, and evidence-backed data flow.
- **BusinessLogicAgent:** domain concepts, invariants, and state transitions.

The orchestrator merges the returned `AgentFinding` objects and asks the model to narrate the resulting code-tour anchors. The public output remains citation-first: claims point to `path:start-end` evidence.

## 2. Custom `.bob/rules/onboarding.md`

```text
# Onboarding Rules

1. Cite evidence: `path/to/file.ext:START-END`.
2. Explain WHY, not just WHAT.
3. Order the tour by "conceptual dependency", not file hierarchy.
4. Prefer 8 tour steps. Reject tours with more than 12 steps.
5. Every tour step must be readable in under 10 minutes.
```

## 3. `agents.md` shipped with RepoPilot

```text
# RepoPilot Onboarding Agent

## Identity
You are the RepoPilot Onboarding Agent. You analyze a software repository and produce a structured onboarding plan for a new developer.

## Constraints
- Every claim MUST cite `path:start-end`.
- Do NOT speculate. If evidence is missing, say so.
- Prefer the repository's own vocabulary over generic terms.
- Never modify files. You are read-only.

## Subagents
- ArchitectureAgent -> module map, entry points, data flow
- BusinessLogicAgent -> core domain concepts, invariants

## Output Schema
Strict JSON conforming to `schemas/onboarding_plan.json`.
```

## 4. Three concrete problem-solving examples

### Example 1 — Repository architecture
The Architecture Agent receives repository context plus a strict JSON schema. It must cite entry-point and module files rather than returning a generic architectural description. The resulting evidence becomes candidates for the eight-step tour.

### Example 2 — Business logic grounding
The Business Logic Agent is explicitly constrained to concepts and invariants visible in source. When the repository does not contain enough evidence, the prompt instructs it to return `insufficient evidence` rather than filling gaps from general knowledge.

### Example 3 — Citation-safe Q&A
Q&A retrieves the top repository chunks before the model sees the question. The prompt tells the model to answer only from those chunks, and `qa.py` filters returned citations so the UI can only surface ranges that were actually retrieved.

## 5. Exact prompts

The runtime prompts are stored in `backend/prompts.py`:

- `ARCHITECTURE_PROMPT`
- `BUSINESS_LOGIC_PROMPT`
- `QA_PROMPT`

Their key contract is JSON-only output, no speculation, and line-range citations.

## 6. Screenshot index

Store submission screenshots under `/evidence/bob_sessions/` with names such as:

- `01_architecture_agent.png`
- `02_business_logic_agent.png`
- `03_narration_agent.png`
- `04_qa_agent.png`

The supplied source bundle did not contain real Bob session screenshots, so these must be captured when the live Bob endpoint is exercised.
