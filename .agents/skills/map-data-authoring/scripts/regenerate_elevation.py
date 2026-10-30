"""Regenerate content/maps/wilderness_elevation.json without the game.

Uses the map editor's environment (it carries the core ``generation`` extra,
NumPy/SciPy). Run from the repository root:

    uv run --locked --project tools/map-editor python \
        .agents/skills/map-data-authoring/scripts/regenerate_elevation.py [--check]

It refuses to generate while the sources fail the static checks of
check_map_sources.py (apart from the stale elevation/partition artifacts),
rereads the sources before publishing and only writes when the continent
source signature is unchanged, replacing the artifact atomically.
``--check`` writes nothing and exits 1 when the committed artifact is not
byte-identical to a fresh run.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_map_sources import _load_reference, game_rules  # noqa: E402
from elosern_map_core import (  # noqa: E402
    AuthoringError,
    diagnose_world,
    discover_source_documents,
    load_authoring_world,
    terrain_definition,
)
from elosern_map_core.diagnostics import blocking as blocking_diagnostics  # noqa: E402
from elosern_map_core.elevation import (  # noqa: E402
    DEFAULT_ELEVATION_CONFIG,
    generate_elevation,
)
from elosern_map_core.elevation_codec import (  # noqa: E402
    DEFAULT_CONFIG_DIGEST,
    ELEVATION_ALGORITHM_VERSION,
    ELEVATION_TILE_CELLS,
    ElevationBudgetExceededError,
    canonical_json,
    encode_elevation_artifact,
    verify_elevation_data_integrity,
)

ELEVATION_PATH = "content/maps/wilderness_elevation.json"


def _load(root: Path):
    return load_authoring_world(discover_source_documents(root))


def _write_atomic(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".wilderness_elevation.", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


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

    blocking = [
        d
        for d in blocking_diagnostics(diagnose_world(world))
        if d.code not in ("stale_partition", "stale_elevation")
    ]
    context, _ = _load_reference(root)
    problems, _warnings = game_rules(world, context)
    if blocking or problems:
        print("refusing to generate: fix these first (see check_map_sources.py):")
        for item in blocking:
            print("  -", item.code, item.message)
        for problem in problems:
            print("  -", problem)
        return 1

    continent_fp = world.fingerprints.get("content/maps/continent.yaml")
    if not continent_fp:
        print("content/maps/continent.yaml is missing from discovered sources")
        return 1

    terrain = terrain_definition(world.continent)
    shapes = world.continent.elevation_shapes
    config = DEFAULT_ELEVATION_CONFIG
    config_dict = asdict(config)
    if isinstance(config_dict.get("prominence_thresholds"), tuple):
        config_dict["prominence_thresholds"] = list(config_dict["prominence_thresholds"])
    config_digest = hashlib.sha256(canonical_json(config_dict).encode("utf-8")).hexdigest()

    print(f"generating elevation for {terrain.frame_cells}x{terrain.frame_cells} frame...")
    rasters = generate_elevation(terrain, config=config, shapes=shapes)

    try:
        text = encode_elevation_artifact(
            bands=rasters.bands,
            tiers=rasters.tiers,
            frame_cells=terrain.frame_cells,
            continent_fingerprint=continent_fp,
            config_digest=config_digest,
            algorithm_version=ELEVATION_ALGORITHM_VERSION,
            tile_cells=ELEVATION_TILE_CELLS,
        )
    except ElevationBudgetExceededError as error:
        print(f"generation failed budget constraint: {error}")
        return 1

    # Verify self-consistency of the encoded text before touching disk
    try:
        verify_elevation_data_integrity(text, expected_frame_cells=terrain.frame_cells)
    except Exception as error:
        print(f"internal validation of generated text failed: {error}")
        return 1

    target = root / ELEVATION_PATH
    current = target.read_text(encoding="utf-8") if target.exists() else None

    if check_only:
        if current == text:
            print(f"{ELEVATION_PATH} is up to date")
            return 0
        print(f"{ELEVATION_PATH} is stale")
        return 1

    if current == text:
        print(f"{ELEVATION_PATH} already up to date; nothing written")
        return 0

    fresh_world = _load(root)
    if fresh_world.fingerprints.get("content/maps/continent.yaml") != continent_fp:
        print("continent source changed during generation; nothing written, run again")
        return 1

    _write_atomic(target, text)

    print(f"wrote {ELEVATION_PATH} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
