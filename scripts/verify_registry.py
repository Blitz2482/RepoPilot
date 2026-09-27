from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_RE = re.compile(r"\| (T-\d{2}\.\d{2}) \|")
EXPECTED_COUNT = 74  # Counted from Bundle v2.0 registry tables, Chapters 27.1–27.5.


def project_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = TASK_RE.match(line)
        if match:
            ids.add(match.group(1))
    return ids


def source_ids(pdf: Path) -> set[str]:
    raw = subprocess.check_output(
        ["pdftotext", "-f", "56", "-l", "62", "-layout", str(pdf), "-"],
        text=True,
    )
    return set(re.findall(r"T-\d{2}\.\d{2}", raw))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify RepoPilot task registry coverage.")
    parser.add_argument("--source-pdf", type=Path, help="Optional supplied Bundle v2.0 PDF for exact source-ID comparison")
    args = parser.parse_args()

    registry = ROOT / "docs/TASK_REGISTRY.md"
    matrix = ROOT / "docs/IMPLEMENTATION_MATRIX.md"
    registry_ids = project_ids(registry)
    matrix_ids = project_ids(matrix)

    if len(registry_ids) != EXPECTED_COUNT:
        raise SystemExit(f"Registry count mismatch: expected {EXPECTED_COUNT}, found {len(registry_ids)}")
    if matrix_ids != registry_ids:
        raise SystemExit(f"Implementation matrix mismatch: missing={sorted(registry_ids - matrix_ids)} extra={sorted(matrix_ids - registry_ids)}")

    if args.source_pdf:
        source = source_ids(args.source_pdf)
        if source != registry_ids:
            raise SystemExit(f"Source mismatch: missing={sorted(source - registry_ids)} extra={sorted(registry_ids - source)}")
        print(f"Source registry alignment PASS ({len(source)} unique task IDs match the supplied PDF registry)")
    else:
        print(f"Project registry alignment PASS ({len(registry_ids)} unique task IDs; matrix matches registry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
