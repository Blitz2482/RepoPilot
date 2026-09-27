from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Secrets must never be committed or included in the release artifact.
secret_patterns = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in {".git", ".pytest_cache", "__pycache__", "node_modules", ".next"} for part in path.parts):
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for pattern in secret_patterns:
        assert not pattern.search(content), f"possible secret pattern found in {path}"

config = (ROOT / "backend/config.py").read_text(encoding="utf-8")
assert 'allow_credentials=False' in (ROOT / "backend/main.py").read_text(encoding="utf-8")
ingest = (ROOT / "backend/ingest.py").read_text(encoding="utf-8")
assert 'GIT_TERMINAL_PROMPT"] = "0"' in ingest
assert 'settings.github_token and settings.allow_private_repos' in ingest
assert 'target.is_symlink()' in (ROOT / "backend/routes.py").read_text(encoding="utf-8")
assert 'parsed_bob.scheme != "https"' in config
assert '"*" in self.allowed_origins' in config
assert 'BOB_LOG_EXCHANGES must be false in production' in config

for path in ROOT.rglob("*.py"):
    if path == Path(__file__) or any(part in {".git", ".pytest_cache", "__pycache__", "node_modules", ".next"} for part in path.parts):
        continue
    content = path.read_text(encoding="utf-8")
    assert not ("subprocess.run(" in content and "shell=True" in content), f"shell subprocess use found in {path}"

# Production configuration must never silently re-enable mock mode.
env = (ROOT / ".env.example").read_text(encoding="utf-8")
assert "BOB_LOG_EXCHANGES=false" in env
assert "DEV_MODE=true" in env and "MOCK_BOB=true" in env and "LOCAL_EMBEDDINGS=true" in env
print("Static security checks PASS")
