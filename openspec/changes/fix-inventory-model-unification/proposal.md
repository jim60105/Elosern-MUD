## Why

Player inventory exists as two disconnected representations: economy/quests/guild write `actor.db.inventory` (a key list), while the localized 拿/丟/給 commands operate purely on Evennia Object containment (audit finding F12). A bought item cannot be dropped or given ("你沒有帶著"), and a picked-up object never appears in `背包`, `sell`, or ACQUIRE progress.

## What Changes

- `db.inventory` (the `ITEM_REGISTRY` key list) remains the canonical inventory record for economy, quests, and web surfaces.
- 拿/丟/給 become synchronized: object containment moves happen together with the canonical key-list delta through `plan_inventory_delta` (or an equivalent single-writer path), so both views always agree.
- Buy/sell/quest reward behavior is unchanged; tests cover the unified round trip.

## Capabilities

### Modified Capabilities

- `equipment-inventory`: one canonical inventory model with synchronized object moves.
- `shop-economy`: bought items materialize a contained object alongside the key-list write.

## Impact

- `commands/localized/general.py` (CmdGet/CmdDrop/CmdGive), `world/rules/equipment.py` (`plan_inventory_delta`), `world/skills/equipment.py` (`list_items`), shop economy stays as-is; command docs updated if wording changes.
