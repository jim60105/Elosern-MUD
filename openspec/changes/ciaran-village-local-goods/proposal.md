# Proposal

## Why

暗影谷村 sells twelve goods from six homes, and four of them belong to the other two villages now that those villages have maps and hosts: the white spider-silk dress and the silk itself come from 幽月谷村's silk grove, and the dew veil and candied blossom come from 翠綠森林村's canopy weavers and blossom garden. The village also has no food or remedy of its own: its fare and herb hosts sell general goods. This change gives 暗影谷村 five local goods, takes the four borrowed ones off its shelves, and rewrites the cards, rooms and dialogue that named them.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- Five new items appended to `world/lore/items/data_elven_village_goods.py`: `ciaran_nightbloom_preserve` and `ciaran_ember_mushroom_skewer` (food), `ciaran_indigo_dye` and `ciaran_crystal_sand` (material), `ciaran_antivenom_tincture` (usable potion that removes the `poisoned` status; the game's first antidote).
- Four goods leave 暗影谷村's shelves: `elven_traditional_robe` and `elven_forest_veil` (from `elven_attire`), `elven_candied_blossom` (from `elven_fare`), `elven_spider_silk` (from `elven_sundries`). They stay on the capital's shelves and on the shelves of the village that makes them.
- The four affected shelves are re-stocked: `elven_fare` holds the two local foods, `elven_sundries` the two local materials, `elven_remedies` gains the tincture beside its two potions, `elven_attire` keeps its two dark-elf garments. `world/rules/rulebook/commerce/ciaran.yaml` follows, at everyday village prices.
- The cards of four hosts (`ciaran_lareneth`, `ciaran_valwyn`, `ciaran_vethiel`, `ciaran_nireth`), the room prose of one home, and the dialogue tables of the same four hosts are rewritten where they name a removed or a new good. Topic IDs are kept; changed scenes move to revision `r3`.
- `docs/lore/items.md` gains five rows and names the making village of the four borrowed goods; `docs/lore/settlement-locations.md` is corrected where it lists them as 暗影谷村 goods; the editorial ledger rows of the touched sources are refreshed.
- `content/map-reference-context.json` is regenerated.
- The rewritten prose is human-reviewed; the line-by-line review is recorded in `docs/lore/ciaran-local-goods-review.md`. No test asserts wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirements of `ciaran-village-commerce`, `ciaran-village-crafts`, `ciaran-village-commons` and `authored-dialogue-content` name no item and hold unchanged; their existing tests derive goods from the registries.

## Impact

- New file: `docs/lore/ciaran-local-goods-review.md`.
- Edited data: `world/lore/items/data_elven_village_goods.py`, `world/rules/rulebook/item_effects.yaml`, `world/lore/settlements/assortments.py`, `world/rules/rulebook/commerce/ciaran.yaml`, `world/lore/npc_profiles/ciaran_homes_a.py`, `world/lore/npc_profiles/ciaran_homes_b.py`, `content/maps/interiors/ciaran_valwyn_home.yaml`, four files under `world/lore/dialogue/content/`.
- Edited documents: `docs/lore/items.md`, `docs/lore/settlement-locations.md`, `docs/development/npc-editorial-review.md`.
- Regenerated: `content/map-reference-context.json`.
- Player-visible effect: a player can no longer buy the white dress, the dew veil, candied blossom or spider silk in 暗影谷村; she buys them in the village that makes them. Pre-release: a development world keeps old merchant stock and runtime personas until its database is reset.
- Not touched: place rows, the item rows of existing goods, the capital's shelves, every file under `openspec/specs/`.
- No child Git repository is needed.

## Batch:

- depends-on: fionnen-village-fare-homes
- depends-on: elven-village-local-goods
- conflicts: shares `world/lore/settlements/assortments.py`, `docs/development/npc-editorial-review.md`, `docs/lore/settlement-locations.md`, `docs/lore/items.md` and `content/map-reference-context.json` with the village home changes, and its dialogue points guests to the other two villages' makers. Apply it last, after `fionnen-village-fare-homes`.
- conflicts: none with `drop-settlement-city-gate-field` and `retire-limbo-city-gates`.
