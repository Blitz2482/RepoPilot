# 3-minute RepoPilot demo script

## 0:00–0:20 — Hook
**On-screen:** RepoPilot title, then a large codebase view.

**Voiceover:** “A new developer can open a repository with tens of thousands of lines and still not know where to start. RepoPilot turns that codebase into a guided onboarding experience with evidence they can inspect.”

## 0:20–0:50 — Submit
**On-screen:** Paste `https://github.com/sindresorhus/ky`, choose Full-Stack, click Analyze Repository.

**Voiceover:** “We start with a normal GitHub URL and the developer’s role. RepoPilot clones a shallow read-only copy and begins analysis immediately.”

## 0:50–1:20 — Live analysis
**On-screen:** Architecture and Business Logic agent cards; progress moves across the pipeline.

**Voiceover:** “Two specialized agents investigate the repository in parallel. One maps structure and entry points; the other focuses on domain concepts and invariants. Every claim is constrained to repository evidence.”

## 1:20–2:00 — Code tour
**On-screen:** Eight tour steps, click through steps 1–3 and show citations.

**Voiceover:** “The findings are synthesized into exactly eight steps, ordered by conceptual dependency. Each step gives a file, a line range, and a short explanation of why that code matters.”

## 2:00–2:30 — Q&A
**On-screen:** Ask `how does retry work?`; click the returned citation.

**Voiceover:** “Now we can ask a repository question. Retrieval selects the relevant code chunks first. The answer is grounded in those chunks, and the citation jumps directly back into the tour.”

## 2:30–3:00 — Bob + close
**On-screen:** Bob configuration and agent session evidence.

**Voiceover:** “Under the hood, RepoPilot is built around IBM Bob 2.0 Agent Mode, custom onboarding rules, and specialized subagents. RepoPilot turns a codebase into a guided tour.”
