import os
import subprocess
import shutil
import tempfile
from collections import Counter
from pathlib import Path

def clone_repo(repo_url: str, job_id: str) -> str:
    """Clones a GitHub repo to a temp directory and returns the local path."""
    base_dir = os.path.join(tempfile.gettempdir(), "repopilot")
    target_dir = os.path.join(base_dir, job_id)

    # Cleanup existing dir if it exists from a previous run
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    os.makedirs(base_dir, exist_ok=True)

    print(f"Cloning {repo_url} to {target_dir}...")

    try:
        # Shallow clone (--depth 1) with 60s timeout
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            check=True,
            timeout=60,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired:
        raise Exception("Clone timed out (repo might be > 100MB or network slow)")
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to clone {repo_url}. Check URL or if repo is private.")
    except FileNotFoundError:
        raise Exception("Git is not installed or not in PATH")

    language = detect_language(target_dir)
    print(f"✅ Successfully cloned. Primary language detected: {language}")
    return target_dir

def detect_language(repo_path: str) -> str:
    """Simple language detection based on file extension counts."""
    ext_counts = Counter()
    skip_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build', '.next'}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            ext = Path(file).suffix.lower()
            if ext:
                ext_counts[ext] += 1

    if not ext_counts:
        return "unknown"

    ext_map = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
        '.tsx': 'TypeScript', '.java': 'Java', '.go': 'Go',
        '.rs': 'Rust', '.rb': 'Ruby', '.cpp': 'C++', '.c': 'C'
    }

    most_common_ext = ext_counts.most_common(1)[0][0]
    return ext_map.get(most_common_ext, most_common_ext)

if __name__ == "__main__":
    print("Running ingest test...")
    try:
        path = clone_repo("https://github.com/sindresorhus/ky", "test-job-123")
        print(f"Test passed! Repo cloned to: {path}")
    except Exception as e:
        print(f"Test failed: {e}")