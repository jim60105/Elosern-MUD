# Proposal

## Why

Two of the three elven villages exist only as a continent cell and a population: `elven_village_eolas` (幽月谷村) and `elven_village_fionnen` (翠綠森林村). A player who walks onto either cell finds nothing to enter, and only 暗影谷村 has a courier station. This change authors both villages as playable local maps with shared interiors and a working courier station, gives all three villages a public bath, and brings the lore document in line.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- Two new settlement documents, `content/maps/settlements/elven_village_eolas.yaml` (9 nodes) and `content/maps/settlements/elven_village_fionnen.yaml` (11 nodes), each with an irregular layout, road bends, one concealed point entrance and a city gate.
- Eight new host-less shared interiors under `content/maps/interiors/`, four per new village. None sets `art_key`.
- One new leaf node, `bathing_pool` (溪池浴場), in `content/maps/settlements/elven_village_ciaran.yaml`, joined to `stream_bend`. No existing ID, coordinate or direction changes.
- Two courier stations that work: `SETTLEMENT_REGISTRY` rows for both villages and `PLACE_REGISTRY` rows `eolas_silverfeather` and `fionnen_silverfeather` with `letter_service=True`.
- Four existing test assertions that pin shipped data stop pinning it. Each is rewritten to assert the logic it stands for; no new key is appended to any of them:
  - the ordered key list and the key-to-kind table in `world/lore/tests/test_settlements.py`;
  - the host-less key set in `world/rules/tests/test_guild_config/test_service_host_roster.py`;
  - the "unplaced anchor" case in `world/quests/tests/test_definitions.py`, which names `elven_village_fionnen` as a location without a map.
- Regenerated artifacts: `world/maps/data/district_partition.json`, `world/maps/data/road_network.json` and `content/map-reference-context.json`.
- `docs/lore/settlement-locations.md` is revised: all three elven villages have a public bath, 幽月谷村 alone keeps a library, the status lines say all three villages have maps, and each new village gets a short case description.
- A new human-reviewed review document, `docs/lore/elven-villages-map-review.md`, records the reading of the captured map images and the prose review. Map shape and prose register are human judgement. No test asserts them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing requirements of `village-ciaran-map` (the village stays a tree; its text is Traditional Chinese and names no wall, gate, guard, market or shop) and `settlement-place-registry` keep holding unchanged, and their existing tests keep proving them.

## Impact

- New files: 2 settlement documents, 8 interior documents, 1 review document.
- Edited data: `content/maps/settlements/elven_village_ciaran.yaml`, `world/lore/settlements/settlements.py`, `world/lore/settlements/places.py`.
- Edited tests (data pins removed, no test added): `world/lore/tests/test_settlements.py`, `world/rules/tests/test_guild_config/test_service_host_roster.py`, `world/quests/tests/test_definitions.py`. One stale comment is corrected in `world/maps/tests/test_settlement_sources.py`.
- Regenerated: the district partition, the road network signature and the map reference context.
- Edited document: `docs/lore/settlement-locations.md`.
- Not touched: `content/maps/locations.yaml`, personal homes, residents' names, service hosts, assortments, commerce, dialogue, room artwork, and every requirement under `openspec/specs/`.
- No child Git repository is needed.

## Batch:

- depends-on: none
- conflicts: none with `unify-artwork-selection` or `retire-classic-art-assets`. Those two changes work in `world/art/`, the gallery server actions, art tests and art documents. This change touches none of those files and sets no `art_key`, so the three may be applied in any order.
