# Proposal

## Why

幽月谷村 and 翠綠森林村 are about to receive their service hosts and homes. The item registry holds almost nothing either village makes: the lore names kiln-baked flatbread, herbs, glass and magic practice for 幽月谷村, and honey, beeswax, archery and woodland dress for 翠綠森林村, but none of these is an item. This change adds eight local goods so the following four village changes have real local produce to put on their shelves.

It is a game-data change. It adds no mechanism and changes no requirement, so it carries no specification delta (`skip_specs: true`) and adds no test.

## What Changes

- Eight new `ItemDefinition` rows in a new slice `world/lore/items/data_elven_village_goods.py`, appended last in `world/lore/items/assembly.py`:
  - 幽月谷村: `eolas_kiln_flatbread` (food), `eolas_herb_tonic` (usable potion), `eolas_glass_pendant` (accessory), `eolas_proving_wand` (main-hand casting weapon).
  - 翠綠森林村: `fionnen_wildflower_honey` (food), `fionnen_beeswax_salve` (usable potion), `fionnen_archer_bracer` (accessory), `fionnen_leafweave_garb` (armor).
- Four new `EquipmentModifierKey` members and four `equipment_effects.yaml` entries for the equipment items; two `item_effects.yaml` entries for the usable potions.
- `docs/lore/items.md` gains one row per new item in the matching category table.
- No price band is added: every item uses an existing `PRICE_TABLE` band. No item is placed on any shelf here; the village changes do that.
- Item names, summaries and the lore rows are human-reviewed prose; the review is recorded in `docs/lore/elven-village-goods-review.md`. No test asserts wording.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing `equipment-inventory`, `item-use-resolution` and `inventory-item-actions` requirements hold unchanged; the load-time validators they describe prove the new rows.

## Impact

- New files: `world/lore/items/data_elven_village_goods.py`, `docs/lore/elven-village-goods-review.md`.
- Edited data: `world/lore/items/assembly.py`, `world/lore/items/vocab.py` (enum members only), `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/item_effects.yaml`.
- Edited documents: `docs/lore/items.md`.
- Regenerated: `content/map-reference-context.json`. Its fingerprint covers `world/lore/**/*.py` and `world/rules/**/*.yaml`, so the item edits make it stale and the contract gate checks it.
- Not touched: `world/lore/economy.py`, assortments, commerce slices, places, profiles, dialogue, every file under `openspec/specs/`, the WebClient (all kinds and icons already exist).
- No child Git repository is needed.

## Batch:

- depends-on: none
- conflicts: none with `unpin-village-test-data` (test files only), and none with the open changes `drop-settlement-city-gate-field` and `retire-limbo-city-gates` (they touch map gate code and documents; this change touches item data only).
- `eolas-village-craft-homes`, `eolas-village-fare-homes`, `fionnen-village-craft-homes` and `fionnen-village-fare-homes` all depend on this change.
