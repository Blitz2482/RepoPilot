from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from config import settings

CLONE_ROOT = Path("/tmp/repopilot")
CLONE_ROOT.mkdir(parents=True, exist_ok=True)


DISPLAYABLE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".cs",
    ".cpp", ".cc", ".c", ".h", ".hpp", ".md", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".txt", ".sql", ".html", ".css", ".scss", ".sh"
}

EXT_LANGUAGES = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
}


def validate_github_url(repo_url: str) -> str:
    value = repo_url.strip()
    if not value:
        raise ValueError("Repository URL is required")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("Only GitHub repository URLs are accepted, e.g. https://github.com/owner/repo")
    path = parsed.path.strip("/")
    if not re.fullmatch(r"[^/]+/[^/]+(?:\.git)?", path):
        raise ValueError("GitHub URL must be https://github.com/owner/repo")
    safe = urlunparse(("https", "github.com", "/" + path, "", "", ""))
    return safe


def _clone_url(repo_url: str) -> str:
    # Authentication is injected through git environment config below so the token
    # never appears in the clone command line or normal application logs.
    return repo_url


def _directory_size_mb(path: Path) -> float:
    total = 0
    for file in path.rglob("*"):
        if file.is_file():
            try:
                total += file.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)


def _default_branch(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def detect_primary_languages(repo_path: str) -> list[str]:
    counts: dict[str, int] = {}
    for path in Path(repo_path).rglob("*"):
        if path.is_symlink() or not path.is_file() or any(part in {".git", "node_modules", "dist", "build", ".next", "__pycache__"} for part in path.parts):
            continue
        lang = EXT_LANGUAGES.get(path.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return [lang for lang, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]


def clone_repo_sync(repo_url: str, job_id: str) -> str:
    safe_url = validate_github_url(repo_url)
    target = CLONE_ROOT / job_id
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if settings.github_token and settings.allow_private_repos:
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"Authorization: Bearer {settings.github_token}"
    cmd = ["git", "clone", "--depth", "1", "--no-tags", _clone_url(safe_url), str(target)]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=settings.clone_timeout_seconds, check=False)
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise TimeoutError(f"GitHub clone timed out after {settings.clone_timeout_seconds} seconds") from exc
    if proc.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        message = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "git clone failed"
        raise RuntimeError(f"GitHub clone failed: {message}")

    size_mb = _directory_size_mb(target)
    if size_mb > settings.max_repo_mb:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(f"Repository exceeds the {settings.max_repo_mb} MB MVP limit")

    return str(target)


async def clone_repo(repo_url: str, job_id: str) -> str:
    import asyncio
    return await asyncio.to_thread(clone_repo_sync, repo_url, job_id)


def list_displayable_files(repo_path: str) -> set[str]:
    base = Path(repo_path)
    paths: set[str] = set()
    for path in base.rglob("*"):
        if path.is_symlink() or not path.is_file() or any(part in {".git", "node_modules", "dist", "build", ".next", "__pycache__"} for part in path.parts):
            continue
        try:
            if path.stat().st_size > settings.max_source_file_mb * 1024 * 1024:
                continue
        except OSError:
            continue
        if path.suffix.lower() in DISPLAYABLE_EXTENSIONS or path.name.lower().startswith("readme"):
            paths.add(str(path.relative_to(base)).replace("\\", "/"))
    return paths


def inspect_repository(repo_path: str, repo_url: str) -> dict:
    files = []
    for path in Path(repo_path).rglob("*"):
        if path.is_file() and not path.is_symlink() and not any(part in {".git", "node_modules", "dist", "build", ".next", "__pycache__"} for part in path.parts):
            files.append(path)
    return {
        "repo_url": repo_url,
        "default_branch": _default_branch(Path(repo_path)),
        "languages": detect_primary_languages(repo_path),
        "file_count": len(files),
    }
