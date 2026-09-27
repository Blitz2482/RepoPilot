# Railway deployment settings

RepoPilot keeps Railway deployment settings documented rather than embedding an
unsupported/deprecated `railway.json` or version-specific TypeScript IaC file.
Use the Railway dashboard or current Railway CLI to connect the repository.

## Service settings

- Source repository: this repository
- Source/root directory: repository root
- Dockerfile path: `backend/Dockerfile`
- Service variable: `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`
- Healthcheck path: `/health`
- Public networking: generate a Railway domain with HTTPS
- Replica count: 1 unless Redis is configured for cross-process progress

The root build context is intentional: the backend Dockerfile copies shared
files from `schemas/`, `.bob/`, `AGENTS.md`, `agents.md`, and `CONTEXT_PACK.md`.

## Deployment inputs

Set the variables documented in `.env.example` and `docs/DEPLOYMENT.md`.
Keep secrets in Railway Variables rather than committing `.env` files.
