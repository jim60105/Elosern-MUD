## 1. Canonical inventory plumbing

- [ ] 1.1 Confirm `plan_inventory_delta` accepts a single-item step and exposes read/write of `db.inventory` (extend if needed without changing callers)
- [ ] 1.2 Add a helper `registry_key_for_object(obj)` mapping a contained Evennia Object to its `ITEM_REGISTRY` key (by object key or db attribute), with `None` for non-registry objects
- [ ] 1.3 In `world/rules/economy.py::buy`, materialize (or reuse) the item's Evennia Object in the character's containment inside the same transaction that writes the key list

## 2. Unified commands

- [ ] 2.1 Rewrite `CmdGet` (`commands/localized/general.py`): resolve object in room, move into character and add the registry key to `db.inventory` in one `transaction.atomic()`
- [ ] 2.2 Rewrite `CmdDrop`: resolve held object (containment first, canonical list as fallback), move to room and remove the key in one transaction
- [ ] 2.3 Rewrite `CmdGive`: resolve held object, move to target and remove the key in one transaction
- [ ] 2.4 Preserve all-or-nothing snapshot/restore on failure for each command

## 3. Docs and tests

- [ ] 3.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the unified behavior
- [ ] 3.2 Tests: buy → `丟`/`給` succeeds (materialized object moved + key removed); `拿` → sell/ACQUIRE sees the item; non-registry object moves containment-only; failed transfer changes nothing
- [ ] 3.3 Run `commands/tests/test_localized.py`, economy, equipment, and ACQUIRE tests
