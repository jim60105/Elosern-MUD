"""Regenerate world/maps/data/district_partition.json without the game.

Uses the map editor's own environment (it carries the core ``generation``
extra, NumPy/SciPy) and exactly the binding the editor's partition job uses,
which tests/test_map_partition_independence.py proves byte-identical to the
game's ``tools.map_district_partition``. Run from the repository root:

    uv run --locked --project tools/map-editor python \
        .agents/skills/map-data-authoring/scripts/regenerate_partition.py [--check]

It refuses to generate while the sources fail the static checks of
check_map_sources.py (apart from the stale partition itself), rereads the
sources before publishing and only writes when their partition signature is
unchanged, replacing the artifact atomically. ``--check`` writes nothing and
exits 1 when the committed artifact is not byte-identical to a fresh run.
Generation takes a few minutes. Do not run it while the editor's own
partition job is generating.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_map_sources import PARTITION_PATH, _load_reference, game_rules  # noqa: E402
from elosern_map_core import (  # noqa: E402
    AuthoringError,
    diagnose_world,
    discover_source_documents,
    load_authoring_world,
)
from elosern_map_core.partition import (  # noqa: E402
    PartitionError,
    generate_partition,
    partition_input,
    world_snapshot,
)


def _load(root: Path):
    return load_authoring_world(discover_source_documents(root))


def main(argv: list[str]) -> int:
    check_only = "--check" in argv[1:]
    positional = [arg for arg in argv[1:] if not arg.startswith("--")]
    root = Path(positional[0] if positional else ".").resolve()
    try:
        world = _load(root)
    except AuthoringError as error:
        print("sources do not load; fix the structure errors first:")
        for item in error.diagnostics:
            print("  -", item.message)
        return 2
    blocking = [d for d in diagnose_world(world) if d.code != "stale_partition"]
    context, _ = _load_reference(root)
    problems, _warnings = game_rules(world, context)
    if blocking or problems:
        print("refusing to generate: fix these first (see check_map_sources.py):")
        for item in blocking:
            print("  -", item.code, item.message)
        for problem in problems:
            print("  -", problem)
        return 1

    signature = world.partition_signature
    print("generating district partition (this takes a few minutes)...")
    try:
        text = generate_partition(partition_input(world_snapshot(world)))
    except PartitionError as error:
        print("generation failed:")
        for problem in error.problems:
            print("  -", problem)
        return 1

    target = root / PARTITION_PATH
    current = target.read_text(encoding="utf-8") if target.exists() else None
    if check_only:
        if current == text:
            print(f"{PARTITION_PATH} is up to date")
            return 0
        print(f"{PARTITION_PATH} is stale")
        return 1
    if current == text:
        print(f"{PARTITION_PATH} already up to date; nothing written")
        return 0
    if _load(root).partition_signature != signature:
        print("sources changed during generation; nothing written, run again")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".district_partition.", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    print(f"wrote {PARTITION_PATH} ({len(text.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
