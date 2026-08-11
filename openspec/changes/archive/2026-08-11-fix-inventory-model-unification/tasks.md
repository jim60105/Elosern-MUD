## 1. Canonical inventory plumbing

- [x] 1.1 Confirm `plan_inventory_delta` accepts a single-item step and exposes read/write of `db.inventory` (extend if needed without changing callers)
- [x] 1.2 Add a helper `registry_key_for_object(obj)` mapping a contained Evennia Object to its `ITEM_REGISTRY` key (explicit `registry_key` attribute first, object key as fallback), with `None` for non-registry objects
- [x] 1.3 In `world/rules/economy.py::buy`, materialize the item's Evennia Object in the character's containment inside the same transaction that writes the key list (one mirror per bought unit)

## 2. Unified commands

- [x] 2.1 Rewrite `CmdGet` (`commands/localized/general.py`): resolve object in room, move into character and add the registry key to `db.inventory` in one `transaction.atomic()`
- [x] 2.2 Rewrite `CmdDrop`: resolve held object (containment first, canonical list as fallback), move to room and remove the key in one transaction; a list-only key materializes its mirror object in the room
- [x] 2.3 Rewrite `CmdGive`: resolve held object, move to target, remove the key and add it to a character-like target's `db.inventory` in one transaction; a list-only key materializes its mirror object at the target
- [x] 2.4 Preserve all-or-nothing on failure for each command: a refused move raises inside the transaction so the database rollback restores every completed move

## 3. Docs and tests

- [x] 3.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the unified behavior
- [x] 3.2 Tests: buy → `丟`/`給` succeeds (materialized object moved + key removed); `拿` → sell/ACQUIRE sees the item; non-registry object moves containment-only; failed transfer changes nothing
- [x] 3.3 Run `commands/tests/test_localized.py`, economy, equipment, and ACQUIRE tests
