# RepoPilot API

## Health
`GET /health` -> liveness response, for example `{"status":"ok","service":"repopilot-api","version":"2.0.0"}`

`GET /ready` -> readiness response. In production it returns HTTP 503 until required configuration, database, and configured Redis are healthy.

## Repository submission
`POST /api/repos`

```json
{"repo_url":"https://github.com/owner/repo","role":"Full-Stack"}
```

Returns HTTP 202:

```json
{"job_id":"uuid","status":"queued"}
```

## Job status
`GET /api/repos/{id}`

## Onboarding plan
`GET /api/repos/{id}/plan`

## Tour
`GET /api/repos/{id}/tour`

## Source evidence
`GET /api/repos/{id}/source?path=src/main.ts&start=1&end=40`

This helper endpoint supports the code viewer while keeping the public plan contract citation-first.

## Grounded Q&A
`POST /api/repos/{id}/ask`

```json
{"question":"How does retry work?"}
```

Returns:

```json
{"answer":"...","citations":[{"path":"src/client.ts","start":20,"end":30}]}
```

## Live progress
`WS /api/repos/{id}/stream`

Events include `snapshot`, `agent_progress`, `complete`, `error`, and `heartbeat`.
