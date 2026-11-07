# Proposal

## Why

Moving or adding a settlement must not require hand-authored road data. The approved design `docs/superpowers/specs/2026-11-07-official-roads-design.md` generates the wilderness road network offline from the terrain and the settlements' gates. This change delivers the parameters, the deterministic generator, its self-check and the committed artifact. `road-network-runtime` then makes the game read that artifact.

## What Changes

- `content/maps/road_network.yaml` joins the authored source set as a new singleton `road_network` document kind. It is optional for an authoring load, so existing fixture worlds and the standalone editor keep loading. Generation refuses to run without it.
- New pure algorithm `elosern_map_core.roads`, on the existing `generation` extra: cost field, terrain distance, relative neighbourhood plus detour repair, routing with reuse, and an independent self-check.
- New stdlib codec `elosern_map_core.roads_codec`: artifact encoding, decoding, metadata and freshness.
- New game adapter `tools/road_network.py` with `--check` and `--preview`, and the committed artifact `world/maps/data/road_network.json`.
- New CI step in `.github/workflows/quality-gate.yml` that runs `tools.road_network --check`.
- `world.rules.travel_cost` gains one public reader of the region speeds, so generation prices terrain from the rulebook instead of a copied table.

Non-goals: anything read at game runtime, sea routes, bridges, road tiers, manual road overrides, world map display, a map editor layer, a "prefer roads" routing rule, and migration between network versions. River passability, walkability and the elevation and partition artifacts do not change.

## Capabilities

### New Capabilities

- `road-network-generation`: authored road parameters, node selection, the road cost field, topology, routing, the generation self-check and the frozen artifact with its freshness.

### Modified Capabilities

None.

## Impact

- Code: `packages/map-core/elosern_map_core/sources.py`, `schema.py`, `documents.py`, `authoring.py`, new `roads.py` and `roads_codec.py`; new `tools/road_network.py`; `world/rules/travel_cost.py`.
- Authored and generated data: new `content/maps/road_network.yaml` and `world/maps/data/road_network.json`.
- Tests: new `tests/test_road_network_generation.py` and `world/maps/tests/test_road_network_command.py`; document-kind pins in `packages/map-core/tests/test_yaml_codec.py` and `tests/test_map_authoring_contract.py`.
- CI manifests: `.github/top-level-shards.json`, `.github/evennia-shards.json`, `.github/workflows/quality-gate.yml`.
- Docs: new `docs/development/road-network.md`; `docs/development/map-authoring-documents.md`; `.agents/skills/map-data-authoring/references/verification.md`.
- Dependencies: none added. `numpy`, `scipy` and `pillow` are already locked.
- Game behaviour: unchanged by this change alone.
- Human-reviewed, not test-established: whether the road distribution looks reasonable, and the tuned parameter values. The review is recorded in the named review document `docs/development/road-network.md`, section "Human review record", from the uncommitted preview image. It does not block this change.

## Batch:

Part of the official roads batch. This change depends on no other change.

Code-conflict notes: this change must merge before `road-network-runtime`, which reads its codec, its artifact and `travel_cost.region_speeds_m_per_hour`. The two changes both touch `.github/evennia-shards.json` and `world/rules/travel_cost.py`, in different places.
