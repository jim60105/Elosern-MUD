# Proposal

## Why

幽月谷村 (`elven_village_eolas`) has a local map and shared places but no personal homes and no hosts, so a player who walks in can buy, sell and talk to nobody. `docs/lore/settlement-locations.md` sets a floor for elven villages: a player must be able to trade and resupply there as in a human town, through individual elves who share what they love making from their own homes. This change adds 3 such homes and hosts, following 暗影谷村.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- 3 new hosts, all elven women of the 伊歐拉斯族: 妮爾內爾‧德米多 (調藥者), 雷林‧莉特弗特 (烤餅好手), 賽爾內爾‧妮格汀加勒 (長老).
- 3 new home interiors under `content/maps/interiors/`, each one room opening from an existing node of the village map. None sets `art_key`.
- 3 new `PlaceDefinition` rows of kind `HOME` in `world/lore/settlements/places_eolas.py` (existing slice).
- 2 new assortments in `world/lore/settlements/assortments.py` with their offers and shop hours in `world/rules/rulebook/commerce/eolas.yaml`. Prices follow the 暗影谷村 pattern: local produce sells at everyday figures in the village that makes it, far below what the capital asks.
- 3 new NPC profiles in the new slice `world/lore/npc_profiles/eolas_homes_b.py`, registered last in `world/lore/npc_profiles/__init__.py`.
- 3 new authored dialogue tables: `world/lore/dialogue/content/eolas_nirnel.yaml`, `world/lore/dialogue/content/eolas_raellin.yaml`, `world/lore/dialogue/content/eolas_saelnel.yaml`.
- The cards, voice lines, room prose and dialogue carry the world source's elven ethic toward the body: no shame about the bare body, about being seen or about sex (`tmp/story_settings/world_info.md` 生活方式 › 性文化, 社會與文化 › 倫理觀; `docs/lore/overview.md` 性愛與身體; `docs/lore/settlement-locations.md` 〈公共浴場〉聚落差異 — 溫泉浴場 is an open pool with no partitions and no attendant, and that contrast is kept as the hook for stories). 賽爾內爾's 外人 scene says the village neither dresses for guests nor hides from them; sex is as natural as breathing here and takes most of the village's time, so the prose says so outright. Frankness rides in what a host says and does — an actor line never grants consent or is written into an act. No line or card names an age or a count of years.
- `world/lore/npc_profiles/inventory.py` and `docs/development/npc-editorial-review.md` gain one `place_host` and one `dialogue_table` entry per host.
- `content/map-reference-context.json` is regenerated.
- `docs/lore/settlement-locations.md` is revised: the 幽月谷村 case description names the village's hosts and what each shares, and the last item of 未來擴充方向 no longer lists 幽月谷村 as waiting for homes and hosts.
- No test is edited. The slice modules this change extends are already enumerated by the tests the previous village change adjusted.
- Cards, voice lines, room prose and dialogue are human-reviewed prose. The line-by-line review is recorded in `docs/lore/eolas-fare-homes-review.md`. No test asserts wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing requirements of `settlement-place-registry`, `npc-profile-registry`, `authored-dialogue-content` and the commerce catalog hold unchanged; their load-time validators and existing tests prove the new rows.

## Impact

- New files: 3 interior documents, 3 dialogue tables, `world/lore/npc_profiles/eolas_homes_b.py`, `docs/lore/eolas-fare-homes-review.md`.
- Edited data: `world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `world/lore/settlements/places_eolas.py`, `world/rules/rulebook/commerce/eolas.yaml`.
- Edited documents: `docs/development/npc-editorial-review.md`, `docs/lore/settlement-locations.md`.
- Regenerated: `content/map-reference-context.json`. Interiors are not partition inputs, so the district partition and the road network stay as they are.
- Not touched: the settlement map document, `content/maps/locations.yaml`, the item registry, every file under `openspec/specs/`, room artwork.
- No child Git repository is needed.

## Batch:

- depends-on: eolas-village-craft-homes
- depends-on: unpin-village-test-data
- depends-on: elven-village-local-goods
- conflicts: the four village home changes edit the same shared files (`world/lore/settlements/assortments.py`, `world/lore/npc_profiles/__init__.py`, `world/lore/npc_profiles/inventory.py`, `docs/development/npc-editorial-review.md`, `content/map-reference-context.json`, and for the first change of each village `world/lore/settlements/places.py`, `world/rules/rulebook/commerce/scales.yaml`, `tools/map_reference_context.py` and two test modules). Apply them one at a time in this order: `eolas-village-craft-homes`, `eolas-village-fare-homes`, `fionnen-village-craft-homes`, `fionnen-village-fare-homes`.
- conflicts: none with the open changes `drop-settlement-city-gate-field` and `retire-limbo-city-gates`, which touch map gate code and documents.
