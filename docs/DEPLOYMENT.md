# RepoPilot Deployment Guide

RepoPilot is a monorepo with a Next.js frontend and FastAPI backend.

## Deployment topology

- **Frontend:** Vercel, Root Directory `frontend`, Framework `Next.js`.
- **Backend:** Railway, repository root as the service source, Dockerfile `backend/Dockerfile`.
- **Database:** PostgreSQL with pgvector. The supplied schema creates the required extensions when the database role permits it.
- **Optional progress bus:** Redis for cross-process WebSocket progress events.

### Railway configuration

The deployment package documents the Railway settings needed for a new service instead of shipping a deprecated Config-as-Code file. Use the Railway dashboard or current CLI to connect the repository.

The service uses the repository root as its build context and sets `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`.

The backend container is intentionally run from `backend/` so `uvicorn main:app` resolves correctly while the Docker build can still copy the shared schema, Bob rules, and context pack from the repository root.

## Backend production variables

Set these in Railway. Values marked `<credential>` are intentionally left for deployment-time configuration.

```text
DATABASE_URL=<Postgres/Supabase connection string>
BOB_API_KEY=<credential>
BOB_BASE_URL=<credential / verified Bob base URL>
BOB_ENDPOINT=<credential / verified Bob endpoint>
OPENAI_API_KEY=<credential>
GITHUB_TOKEN=<credential, optional for private repos>
ALLOW_PRIVATE_REPOS=false
SENTRY_DSN=<credential, optional>
REDIS_URL=<optional Redis connection string>
CORS_ORIGINS=https://<your-vercel-domain>

DEV_MODE=false
MOCK_BOB=false
LOCAL_EMBEDDINGS=false
BOB_LOG_EXCHANGES=false

MAX_REPO_MB=100
MAX_PARSED_FILE_MB=5
MAX_SOURCE_FILE_MB=2
CLONE_TIMEOUT_SECONDS=60
NODE_TIMEOUT_SECONDS=120
PIPELINE_TIMEOUT_SECONDS=300
MAX_CONCURRENT_JOBS=2
MAX_QUESTION_CHARS=500
SOURCE_MAX_LINES=400
JOB_RETENTION_HOURS=24
```

The source bundle requires the database, Bob/OpenAI, and deployment configuration; the actual Bob API contract is external to the bundle and must be filled from the hackathon service specification.

## Frontend production variables

Set this in Vercel:

```text
NEXT_PUBLIC_API_URL=https://<your-railway-domain>
NEXT_PUBLIC_SENTRY_DSN=<credential, optional>
```

The frontend must use the public HTTPS backend. Its WebSocket helper converts `https://` to `wss://` automatically.

## Pre-deploy environment validation

After adding the real secret values to Railway/Vercel, run this from the repository root: 

```bash
python scripts/verify_production_env.py
```

The check validates the production mode switches, required secret/config variable presence, HTTPS Bob URL, explicit CORS origins, and the private-repository access switch without printing secret values.

## Database initialization

Apply `backend/schema.sql` once to the target PostgreSQL/Supabase project. The application also attempts schema initialization at startup when `DATABASE_URL` is configured.

The schema follows the bundle's required core entities/index structures and keeps vector embeddings at 1536 dimensions.

## Railway deployment

### Option A — Railway dashboard

1. Create a Railway project.
2. Add a service from the GitHub repository.
3. Keep the service source root at the repository root.
4. Set the service variable `RAILWAY_DOCKERFILE_PATH=backend/Dockerfile`.
5. Add the backend production variables above.
6. Generate a public domain for the service.
7. Verify `GET /health` returns HTTP 200 and `GET /ready` returns HTTP 200.

Railway provides public domains with automatic SSL, and a generated domain can be added from the service's Public Networking settings.

### Option B — Railway CLI

From the repository root, use the current Railway CLI workflow:

```bash
railway login
railway link
railway up
```

The repository contains `.railway/README.md` and `docs/RAILWAY_SETTINGS.json` as the deployment settings reference. Use the current Railway dashboard or CLI workflow to apply these settings; this avoids depending on a version-specific IaC command or deprecated Config-as-Code file.

## Vercel deployment

1. Import the repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Keep framework detection as Next.js.
4. Set `NEXT_PUBLIC_API_URL` to the public Railway backend URL.
5. Deploy.

The production build intentionally fails early when `NEXT_PUBLIC_API_URL` is missing so a misconfigured frontend cannot be promoted as a working deployment.

## Production verification checklist

Run these checks after both services are deployed:

```bash
# backend
curl -i https://<railway-domain>/health
curl -i https://<railway-domain>/ready
curl -i https://<railway-domain>/openapi.json
curl -i https://<railway-domain>/metrics

# frontend
open https://<vercel-domain>
```

Then submit a small public GitHub repository and verify:

```text
POST /api/repos -> 202 + job_id
WS  /api/repos/{job_id}/stream -> snapshot + progress + complete
GET /api/repos/{job_id}/plan -> 200 + exactly 8 tour steps
GET /api/repos/{job_id}/tour -> 200 + 8 tour steps
GET /api/repos/{job_id}/source -> citation source content
POST /api/repos/{job_id}/ask -> answer + grounded citations
```

These routes implement the public API surface defined by the bundle.

## Important deployment limitation

RepoPilot's MVP background pipeline is intentionally simple and runs inside the API service. For the hackathon-sized deployment, run one backend replica unless you also provision Redis. Redis is supported for cross-process progress publication; completed plans persist in PostgreSQL. The application restores completed jobs from PostgreSQL after a process restart.
