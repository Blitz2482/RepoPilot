from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], *, cwd: Path = ROOT, extra_env: dict[str, str] | None = None) -> None:
    print("$", " ".join(cmd))
    env = None
    if extra_env:
        import os
        env = os.environ.copy()
        env.update(extra_env)
    result = subprocess.run(cmd, cwd=cwd, check=False, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


run([sys.executable, "-m", "compileall", "-q", "backend", "scripts"])
run([sys.executable, "scripts/verify_deployment.py"])
run([sys.executable, "scripts/security_static_check.py"])
run([sys.executable, "scripts/verify_registry.py"])
run(["node", "scripts/verify_frontend_config.mjs"])
run(["node", "scripts/verify_frontend_syntax.mjs"])
run([sys.executable, "-m", "pytest", "-q", "backend"])

frontend = ROOT / "frontend"
require_frontend = __import__("os").environ.get("REQUIRE_FRONTEND_BUILD", "0") == "1"
if (frontend / "node_modules").is_dir():
    run(["npm", "run", "typecheck"], cwd=frontend, extra_env={"NEXT_PUBLIC_API_URL": "https://example.invalid"})
    run(["npm", "run", "build"], cwd=frontend, extra_env={"NEXT_PUBLIC_API_URL": "https://example.invalid"})
else:
    if require_frontend:
        raise SystemExit("Frontend install/build was required but frontend/node_modules is absent")
    print("Frontend install/build: SKIPPED (frontend/node_modules is not installed in this environment).")
    print("CI is configured to install dependencies and run both `npm run typecheck` and `npm run build`.")

print("Release verification PASS")
print("Note: live IBM Bob, PostgreSQL/pgvector, Redis, Vercel and Railway services require deployment-time credentials/accounts.")
