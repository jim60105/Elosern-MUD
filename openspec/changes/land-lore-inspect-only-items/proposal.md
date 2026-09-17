## Why

`docs/lore/items.md` is the world-building source of truth for the item catalog, and it was just reconciled against the shipped code: every entry now carries a stable `key`, a price band that its reference price actually fits, and a rarity whose budget its numbers respect. The registry it describes has not caught up — `ITEM_REGISTRY` holds 58 items that were authored early to get the economy running, and 48 catalogued items have no data at all.

With the provisional data replaced by `replace-temp-item-data`, this change lands the easiest and largest slice: the 24 inspect-only items (food, non-mechanical remedies, tools, materials, curios). They carry no use mechanics and no equipment slot, so they need no rulebook entry and no new vocabulary member — they are pure identity data plus the one price band the food tier needs. Landing them first establishes the catalog contract that the equipment and sex-toy slices then extend.

## What Changes

- Add a `specialty_food` price band (10–100 copper) to `PRICE_TABLE` for regional delicacies, which sit above an ordinary meal but far below any equipment.
- Register 24 inspect-only `ItemDefinition` entries from the lore codex: 6 foods, 5 non-mechanical remedies, 4 tools, 6 materials, 3 curios. Every one declares neither `use_mechanics` nor `equipment_slot`.
- Stock 18 of them in the existing Altoria general store (`SHOP_REGISTRY` offered keys plus `guild_economy.yaml` offers), with stock depth scaled to rarity.
- Leave 6 out of the store on lore grounds: 精靈之淚 and 精靈體液 reach humans by gift rather than trade, 古龍心臟 has no trade record on the continent, and the three curios are non-sellable narrative props.
- Record in `docs/lore/items.md` that the 雜物 category lands as `sellable = false` on the `relic` band, mirroring the shipped `guild_recruit_badge`.
- Specify three shape-derived behavioral invariants — inert items refuse mechanics by name, non-sellability outranks a shop listing, and an unstocked item is still fully functional — each covered by a synthetic-fixture test.
- No behavior change to the engine: no new enum member, no rulebook verb, no settlement path is touched. **No new game-data contract test is added**; the codex stays a reviewed design document and the mechanical guarantees stay with the loaders that already fail closed.

## Capabilities

### Modified Capabilities
- `lore-item-catalog`: gains three shape-derived invariants alongside the retirement invariant `replace-temp-item-data` opened it with — what an item with no mechanics may and may not do, what non-sellability blocks, and what registration does and does not entitle an item to. Every one is satisfiable and testable with a synthetic item, so nothing in it names shipped content.
- `lore-registries`: the `PRICE_TABLE` requirement enumerates the bands it must cover; it gains the regional-delicacy band.

## Impact

- `world/lore/economy.py` — one new `PriceEntry`.
- `world/lore/items.py` — 24 new `ItemDefinition` entries in `ITEM_REGISTRY`.
- `world/lore/shops.py` — 18 new keys in the general store's `offered_item_keys`.
- `world/rules/rulebook/guild_economy.yaml` — 18 new shop offers.
- `docs/lore/items.md` — one clarifying line in the 雜物 section.
- Two already-registered data-contract tests get their literals moved and nothing more: `world/lore/tests/test_items.py` (exact key set) and `world/rules/tests/test_guild_config.py` (literal registry count). No ledger entry is added to `tools/test_data_freeze.json`.
- Three new behavior tests on synthetic fixtures, added to existing test modules so `.github/evennia-shards.json` is untouched.
- No consumer of `ITEM_REGISTRY` changes shape; every new entry is inspect-only, which is the one item form every existing consumer already handles.
- Runs after `replace-temp-item-data`, which opens the `lore-item-catalog` capability and finalises the 58 shipped entries this change adds beside.
