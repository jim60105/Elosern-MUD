# Proposal

## Why

The approved design `docs/superpowers/specs/2026-11-07-official-roads-design.md` generates the wilderness road network offline. The generator and the game both need one shared definition first: the authored parameters and the artifact format with its freshness rule. This change delivers that shared format. It holds no road algorithm.

## What Changes

- `content/maps/road_network.yaml` joins the authored source set as a new singleton `road_network` document kind. It is optional for an authoring load, so existing fixture worlds and the standalone editor keep loading.
- New stdlib codec `elosern_map_core.roads_codec`: artifact encoding, decoding, metadata, source signature and freshness.
- `world.rules.travel_cost` gains one public reader of the region speeds, so generation prices terrain from the rulebook instead of a copied table.

Non-goals: the road algorithm, the committed artifact, anything read at game runtime, and any map editor change. The elevation and partition artifacts stay current when road parameters change.

## Capabilities

### New Capabilities

- `road-network-artifact`: the authored road parameter document and the frozen road artifact's decoding and freshness.

### Modified Capabilities

None.

## Impact

- Code: `packages/map-core/elosern_map_core/sources.py`, `schema.py`, `documents.py`, `authoring.py`, new `roads_codec.py`; `world/rules/travel_cost.py`.
- Authored data: new `content/maps/road_network.yaml`.
- Generated data: `content/map-reference-context.json` is regenerated, because its manifest hashes the edited map-core and rule sources.
- Tests: new `tests/test_road_network_format.py`; document-kind pins in `packages/map-core/tests/test_yaml_codec.py` and `tests/test_map_authoring_contract.py`.
- CI manifest: `.github/top-level-shards.json`.
- Docs: `docs/development/map-authoring-documents.md`.
- Dependencies: none added. Game behaviour is unchanged.
- Human-reviewed: nothing in this change.

## Batch:

Part of the official roads batch. This change depends on no other change.

Code-conflict notes: merges before `road-network-generation` and `road-network-runtime`. All three regenerate `content/map-reference-context.json`, and all three touch `world/rules/travel_cost.py` or map-core sources, so apply them in order and regenerate last in each.
