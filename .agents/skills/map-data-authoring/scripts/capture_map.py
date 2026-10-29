"""Capture one authored map view as a lossless image, offline.

Run from the source workspace root in the locked capture environment:

    uv run --locked --no-sync --project tools/map-editor --group capture python \
        .agents/skills/map-data-authoring/scripts/capture_map.py \
        --view continent --output /tmp/continent.webp

The command, its arguments and every per-view layer are documented in the
skill's `references/verification.md` and `SKILL.md`. The orchestration lives
in `elosern_map_editor.capture`; this file is only the entry point.
"""

from __future__ import annotations

import sys

from elosern_map_editor.capture import main

if __name__ == "__main__":
    sys.exit(main())
