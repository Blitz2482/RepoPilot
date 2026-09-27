from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".env.example",
    ".dockerignore",
    ".nvmrc",
    ".railway/README.md",
    "docs/RAILWAY_SETTINGS.json",
    "scripts/verify_production_env.py",
    ".github/workflows/ci.yml",
    "backend/Dockerfile",
    "backend/requirements.txt",
    "backend/schema.sql",
    "frontend/package.json",
    "frontend/vercel.json",
    "frontend/app/page.tsx",
    "AGENTS.md",
]

for rel in REQUIRED_FILES:
    assert (ROOT / rel).exists(), f"missing required deployment file: {rel}"

assert not (ROOT / "railway.json").exists(), "deprecated root railway.json should not be used for new Railway services"
assert not (ROOT / "backend/railway.json").exists(), "deprecated nested Railway config should not shadow IaC"

railway = json.loads((ROOT / "docs/RAILWAY_SETTINGS.json").read_text())
assert railway.get("source_root") == "."
assert railway.get("dockerfile_path") == "backend/Dockerfile"
assert railway.get("healthcheck_path") == "/health"
assert railway.get("required_variable", {}).get("RAILWAY_DOCKERFILE_PATH") == "backend/Dockerfile"
assert "dashboard" in (ROOT / ".railway/README.md").read_text().lower()

vercel = json.loads((ROOT / "frontend/vercel.json").read_text())
assert vercel.get("framework") == "nextjs"
assert vercel.get("version") == 2

pkg = json.loads((ROOT / "frontend/package.json").read_text())
assert pkg["engines"]["node"] == ">=20 <25"
assert pkg["engines"]["npm"] == ">=10 <12"
assert "typecheck" in pkg["scripts"]
assert pkg["scripts"]["build"] == "next build"
for section in ("dependencies", "devDependencies"):
    for name, version in pkg[section].items():
        assert not version.startswith(("^", "~")), f"frontend dependency {name} is not pinned"

# Verify every Docker COPY source exists in the repository root build context.
dockerfile = (ROOT / "backend/Dockerfile").read_text()
copy_sources = re.findall(r"^COPY\s+(\S+)", dockerfile, flags=re.M)
for source in copy_sources:
    source_path = ROOT / source.rstrip("/")
    assert source_path.exists(), f"Docker COPY source missing from root build context: {source}"
assert re.search(r"FROM\s+python:3\.11-slim", dockerfile)
assert re.search(r"^USER\s+repopilot$", dockerfile, flags=re.M)
assert "EXPOSE 8000" in dockerfile
assert "/health" in dockerfile and "HEALTHCHECK" in dockerfile
assert "USER repopilot" in dockerfile
assert "uvicorn main:app" in dockerfile

# Verify key environment contracts without requiring credential values.
env = (ROOT / ".env.example").read_text()
for key in [
    "DATABASE_URL", "BOB_API_KEY", "BOB_BASE_URL", "BOB_ENDPOINT", "OPENAI_API_KEY",
    "GITHUB_TOKEN", "ALLOW_PRIVATE_REPOS", "CORS_ORIGINS", "REDIS_URL", "DEV_MODE", "MOCK_BOB", "LOCAL_EMBEDDINGS",
    "MAX_REPO_MB", "MAX_PARSED_FILE_MB", "MAX_SOURCE_FILE_MB", "CLONE_TIMEOUT_SECONDS", "PIPELINE_TIMEOUT_SECONDS",
]:
    assert re.search(rf"^{re.escape(key)}=", env, flags=re.M), f"missing environment variable: {key}"
schema = (ROOT / "backend/schema.sql").read_text()
assert "ADD COLUMN IF NOT EXISTS code_chunks_fts tsvector" in schema
assert "UPDATE code_chunks" in schema and "WHERE code_chunks_fts IS NULL" in schema
assert not (ROOT / ".env").exists(), "real .env must not be committed or packaged"
assert not (ROOT / "frontend/.env.local").exists(), "local frontend env must not be committed or packaged"
frontend_env = (ROOT / "frontend/.env.example").read_text()
for key in ("NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_SENTRY_DSN"):
    assert re.search(rf"^{re.escape(key)}=", frontend_env, flags=re.M), f"missing frontend environment variable: {key}"

print("Deployment structure verification PASS")

api_ts = (ROOT / "frontend/lib/api.ts").read_text()
assert "NEXT_PUBLIC_API_URL must use HTTPS in production" in api_ts, "missing production HTTPS guard"

assert (ROOT / "AGENTS.md").read_text() == (ROOT / "agents.md").read_text(), "AGENTS.md and agents.md must stay synchronized"

bob_client = (ROOT / "backend/bob_client.py").read_text()
assert "timeout=min(settings.node_timeout_seconds, 25)" in bob_client, "OpenAI provider timeout must be bounded below the graph node timeout"
