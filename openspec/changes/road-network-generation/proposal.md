# Proposal

## Why

Moving or adding a settlement must not require hand-authored road data. The approved design `docs/superpowers/specs/2026-11-07-official-roads-design.md` generates the wilderness road network offline from the terrain and the settlements' gates. On top of the parameter document and codec from `road-network-format`, this change delivers the deterministic generator, its self-check and the committed artifact. `road-network-runtime` then makes the game read that artifact.

## What Changes

- New pure algorithm `elosern_map_core.roads`, on the existing `generation` extra: cost field, terrain distance, relative neighbourhood plus detour repair, routing with reuse, and an independent self-check.
- New game adapter `tools/road_network.py` with `--check` and `--preview`, and the committed artifact `world/maps/data/road_network.json`.
- New CI step in `.github/workflows/quality-gate.yml` that runs `tools.road_network --check`.

Non-goals: anything read at game runtime, sea routes, bridges, road tiers, manual road overrides, world map display, a map editor layer, a "prefer roads" routing rule, and migration between network versions. River passability, walkability and the elevation and partition artifacts do not change.

## Capabilities

### New Capabilities

- `road-network-generation`: node selection, the road cost field, topology, routing, the generation self-check and the regeneration command.

### Modified Capabilities

None.

## Impact

- Code: new `packages/map-core/elosern_map_core/roads.py`; new `tools/road_network.py`.
- Generated data: new `world/maps/data/road_network.json`; `content/map-reference-context.json` is regenerated, because its manifest hashes map-core sources.
- Tests: new `tests/test_road_network_generation.py` and `world/maps/tests/test_road_network_command.py`.
- CI manifests: `.github/top-level-shards.json`, `.github/evennia-shards.json`, `.github/workflows/quality-gate.yml`.
- Docs: new `docs/development/road-network.md`; `.agents/skills/map-data-authoring/references/verification.md`.
- Dependencies: none added. `numpy`, `scipy` and `pillow` are already locked.
- Game behaviour: unchanged by this change alone.
- Human-reviewed, not test-established: whether the road distribution looks reasonable, and the tuned parameter values. The review is recorded in the named review document `docs/development/road-network.md`, section "Human review record", from the uncommitted preview image. It does not block this change.

## Batch:

Part of the official roads batch.

depends-on: road-network-format

Code-conflict notes: merges after `road-network-format` and before `road-network-runtime`, which reads this change's artifact. All three regenerate `content/map-reference-context.json`, and this change and `road-network-runtime` touch `.github/evennia-shards.json`, so apply them in order.
