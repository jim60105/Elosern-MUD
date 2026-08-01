"""Assert that a Coverage.py JSON report contains every configured source root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tomllib
from collections.abc import Sequence


def configured_roots(pyproject_path: Path) -> set[str]:
    """Read the source roots configured for Coverage.py."""
    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    roots = config["tool"]["coverage"]["run"]["source"]
    if not isinstance(roots, list) or any(not isinstance(root, str) for root in roots):
        raise ValueError("tool.coverage.run.source must be a list of strings")
    return set(roots)


def reported_roots(report_path: Path) -> set[str]:
    """Return top-level paths represented in a Coverage.py JSON report."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    files = report.get("files")
    if not isinstance(files, dict):
        raise ValueError("coverage report must contain a files object")
    return {Path(filename).parts[0] for filename in files if Path(filename).parts}


def missing_roots(report_path: Path, pyproject_path: Path) -> set[str]:
    """Return configured source roots absent from the combined report."""
    return configured_roots(pyproject_path) - reported_roots(report_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args(argv)
    try:
        missing = missing_roots(args.report, args.pyproject)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"coverage root verification failed: {exc}", file=sys.stderr)
        return 1
    if missing:
        print(f"coverage report is missing configured roots: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    print("coverage report contains every configured source root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
