"""Strict validate CLI for the prompt library (admin pre-restart check).

Usage:
    uv run --locked python -m world.prompts.validate

Loads the prompt library from ``PROMPT_ROOT`` and prints a per-key success
summary or every named error with its file, key, and problem, exiting 0 on
success and 1 on failure, so an admin can verify prompt edits before restarting
the server.
"""

from __future__ import annotations

import sys

from world.prompts.loader import load_prompt_library
from world.prompts.registry import PROMPT_SPECS


def main() -> int:
    """Validate the configured prompt library and print the summary."""
    library = load_prompt_library()
    errors = sorted(library.errors.items())
    if not errors:
        print(
            f"prompt library OK: {len(library.texts)} keys loaded from {library.root}"
        )
        for key in sorted(PROMPT_SPECS):
            print(f"  ok {key}")
        return 0
    print(
        f"prompt library has {len(errors)} error(s) in {library.root}"
    )
    for key, error in errors:
        print(f"  error {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())