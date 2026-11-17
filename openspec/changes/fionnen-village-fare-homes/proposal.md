# Proposal

## Why

翠綠森林村 (`elven_village_fionnen`) has a local map and shared places but no personal homes and no hosts, so a player who walks in can buy, sell and talk to nobody. `docs/lore/settlement-locations.md` sets a floor for elven villages: a player must be able to trade and resupply there as in a human town, through individual elves who share what they love making from their own homes. This change adds 4 such homes and hosts, following 暗影谷村.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- 4 new hosts, all elven women of the 斐歐恩族: 埃倫溫‧斯威夫塔羅 (箭術導師), 菲爾溫‧埃文斯塔爾 (長老), 盧梅斯‧布瑞特莉夫 (蜜漬好手), 希拉拉‧希倫特布魯克 (藥草者).
- 4 new home interiors under `content/maps/interiors/`, each one room opening from an existing node of the village map. None sets `art_key`.
- 4 new `PlaceDefinition` rows of kind `HOME` in `world/lore/settlements/places_fionnen.py` (existing slice).
- 2 new assortments in `world/lore/settlements/assortments.py` with their offers and shop hours in `world/rules/rulebook/commerce/fionnen.yaml`. Prices follow the 暗影谷村 pattern: local produce sells at everyday figures in the village that makes it, far below what the capital asks.
- 4 new NPC profiles in the new slice `world/lore/npc_profiles/fionnen_homes_b.py`, registered last in `world/lore/npc_profiles/__init__.py`.
- 4 new authored dialogue tables: `world/lore/dialogue/content/fionnen_elunwen.yaml`, `world/lore/dialogue/content/fionnen_firwen.yaml`, `world/lore/dialogue/content/fionnen_lumeth.yaml`, `world/lore/dialogue/content/fionnen_sylara.yaml`.
- `world/lore/npc_profiles/inventory.py` and `docs/development/npc-editorial-review.md` gain one `place_host` and one `dialogue_table` entry per host.
- `content/map-reference-context.json` is regenerated.
- `docs/lore/settlement-locations.md` is revised: the 翠綠森林村 case description names the village's hosts and what each shares, and the last item of 未來擴充方向 no longer lists 翠綠森林村 as waiting for homes and hosts.
- No test is edited. The slice modules this change extends are already enumerated by the tests the previous village change adjusted.
- Cards, voice lines, room prose and dialogue are human-reviewed prose. The line-by-line review is recorded in `docs/lore/fionnen-fare-homes-review.md`. No test asserts wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing requirements of `settlement-place-registry`, `npc-profile-registry`, `authored-dialogue-content` and the commerce catalog hold unchanged; their load-time validators and existing tests prove the new rows.

## Impact

- New files: 4 interior documents, 4 dialogue tables, `world/lore/npc_profiles/fionnen_homes_b.py`, `docs/lore/fionnen-fare-homes-review.md`.
- Edited data: `world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `world/lore/settlements/places_fionnen.py`, `world/rules/rulebook/commerce/fionnen.yaml`.
- Edited documents: `docs/development/npc-editorial-review.md`, `docs/lore/settlement-locations.md`.
- Regenerated: `content/map-reference-context.json`. Interiors are not partition inputs, so the district partition and the road network stay as they are.
- Not touched: the settlement map document, `content/maps/locations.yaml`, the item registry, every file under `openspec/specs/`, room artwork.
- No child Git repository is needed.

## Batch:

- depends-on: fionnen-village-craft-homes
- depends-on: unpin-village-test-data
- depends-on: elven-village-local-goods
- conflicts: the four village home changes edit the same shared files (`world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `docs/development/npc-editorial-review.md`, `content/map-reference-context.json`, and for the first change of each village `world/lore/settlements/places.py`, `world/rules/rulebook/commerce/scales.yaml`, `tools/map_reference_context.py` and two test modules). Apply them one at a time in this order: `eolas-village-craft-homes`, `eolas-village-fare-homes`, `fionnen-village-craft-homes`, `fionnen-village-fare-homes`.
- conflicts: none with the open changes `drop-settlement-city-gate-field` and `retire-limbo-city-gates`, which touch map gate code and documents.
