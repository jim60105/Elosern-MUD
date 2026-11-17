# Proposal

## Why

翠綠森林村 (`elven_village_fionnen`) has a local map and shared places but no personal homes and no hosts, so a player who walks in can buy, sell and talk to nobody. `docs/lore/settlement-locations.md` sets a floor for elven villages: a player must be able to trade and resupply there as in a human town, through individual elves who share what they love making from their own homes. This change adds 3 such homes and hosts, following 暗影谷村.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- 3 new hosts, all elven women of the 斐歐恩族: 科瑞斯‧蒙希斯佩爾 (巧作者), 格威內爾‧斯威夫塔羅 (弓匠), 伊斯爾林‧斯塔爾威維爾 (織衣者).
- 3 new home interiors under `content/maps/interiors/`, each one room opening from an existing node of the village map. None sets `art_key`.
- 3 new `PlaceDefinition` rows of kind `HOME` in `world/lore/settlements/places_fionnen.py` (new slice, registered in `world/lore/settlements/places.py` after the 暗影谷村 slice and the 幽月谷村 slice).
- 3 new assortments in `world/lore/settlements/assortments.py` with their offers and shop hours in `world/rules/rulebook/commerce/fionnen.yaml` (new file), and a `price_scales` entry for the village in `world/rules/rulebook/commerce/scales.yaml`. Prices follow the 暗影谷村 pattern: local produce sells at everyday figures in the village that makes it, far below what the capital asks.
- 3 new NPC profiles in the new slice `world/lore/npc_profiles/fionnen_homes_a.py`, registered last in `world/lore/npc_profiles/__init__.py`.
- 3 new authored dialogue tables: `world/lore/dialogue/content/fionnen_corith.yaml`, `world/lore/dialogue/content/fionnen_gwynnel.yaml`, `world/lore/dialogue/content/fionnen_ithrlin.yaml`.
- `world/lore/npc_profiles/inventory.py` and `docs/development/npc-editorial-review.md` gain one `place_host` and one `dialogue_table` entry per host.
- `content/map-reference-context.json` is regenerated.
- Two existing tests that list the place slice modules each gain the new module, with no new assertion on shipped data: the slice-order case in `world/lore/tests/test_settlements.py` and the module list in `tests/test_map_runtime_contract.py`. `tools/map_reference_context.py` gains the new module in its place-source lookup.
- Host cards, voice lines, room prose and dialogue follow the world source's 性文化 and 倫理觀: no shame about sex or the bare body, the weaver's dress worn thin on purpose, and the intimacy goods `tremor_crystal` (恆振晶) and `embracing_vine` (纏枝魔藤) on the 巧作者's shelf.
- Cards, voice lines, room prose and dialogue are human-reviewed prose. The line-by-line review is recorded in `docs/lore/fionnen-craft-homes-review.md`. No test asserts wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing requirements of `settlement-place-registry`, `npc-profile-registry`, `authored-dialogue-content` and the commerce catalog hold unchanged; their load-time validators and existing tests prove the new rows.

## Impact

- New files: 3 interior documents, 3 dialogue tables, `world/lore/npc_profiles/fionnen_homes_a.py`, `docs/lore/fionnen-craft-homes-review.md`, `world/lore/settlements/places_fionnen.py`, `world/rules/rulebook/commerce/fionnen.yaml`.
- Edited data: `world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `world/lore/settlements/places.py`, `world/rules/rulebook/commerce/scales.yaml`.
- Edited documents: `docs/development/npc-editorial-review.md`.
- Regenerated: `content/map-reference-context.json`. Interiors are not partition inputs, so the district partition and the road network stay as they are.
- Not touched: the settlement map document, `content/maps/locations.yaml`, the item registry, every file under `openspec/specs/`, room artwork.
- No child Git repository is needed.

## Batch:

- depends-on: eolas-village-fare-homes
- depends-on: unpin-village-test-data
- depends-on: elven-village-local-goods
- conflicts: the four village home changes edit the same shared files (`world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `docs/development/npc-editorial-review.md`, `content/map-reference-context.json`, and for the first change of each village `world/lore/settlements/places.py`, `world/rules/rulebook/commerce/scales.yaml`, `tools/map_reference_context.py` and two test modules). Apply them one at a time in this order: `eolas-village-craft-homes`, `eolas-village-fare-homes`, `fionnen-village-craft-homes`, `fionnen-village-fare-homes`.
- conflicts: none with the open changes `drop-settlement-city-gate-field` and `retire-limbo-city-gates`, which touch map gate code and documents.
