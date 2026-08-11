## Context

`buy` writes `actor.db.inventory = list(inventory_plan.after)` (`world/rules/economy.py:194`); `sell` reads and rewrites the same list (`economy.py:244,266`); `plan_inventory_delta` (`world/rules/equipment.py:74-128`) is the sole key-list planner for quest/guild/NPC-intent flows. In parallel, `CmdGet`/`CmdDrop`/`CmdGive` (`commands/localized/general.py:146-181,199-284`) move Evennia Objects without touching the key list, so the two views diverge. The key list is the cheaper, already-single-writer model; containment moves are Evennia-native UX (search by name, room placement, give to NPCs).

## Goals / Non-Goals

**Goals:**
- One canonical key list; containment mirrors it.
- Atomic, all-or-nothing transfers.

**Non-Goals:**
- Replacing Evennia object containment with a pure key-list model (objects still exist for room presence, giving, dropping).
- Changing buy/sell math or stock rules.
- Web-side equip actions (none exist).

## Decisions

**D1 — Canonical record = `db.inventory` key list (registry items).** All reads (`背包`, sell, ACQUIRE, turn-in) continue to read the list; object containment is a mirror for command UX. Non-registry Evennia objects are containment-only by design and never enter the key list. Key-only acquisition flows (quest rewards, guild rewards, NPC intent transfers) remain list-only at grant time — their mirror object is materialized on first 拿/丟/給 use (see D5); the key list is authoritative in every partial-mirror state.

**D2 — Mirror identity = explicit `registry_key` attribute.** `materialize_registry_object` (in `world/rules/equipment.py`) creates the contained Evennia Object with both `db_key` and a `registry_key` attribute; `registry_key_for_object` resolves the attribute first and falls back to a matching object key. The attribute wins so scene objects authored with a name that happens to equal a registry key never enter the canonical inventory by accident.

**D3 — Buy materializes mirrors; sell removes them.** `buy` materializes one contained object per bought unit inside the same transaction that writes the key list, so drop/give always have a real object to move. `sell` deletes the contained registry objects of the sold units in the same transaction (D4).

**D4 — Sell removes the mirrored contained objects.** A sale that removes key entries deletes the same number of contained registry objects (matched via `registry_key_for_object`) inside the same transaction; when containment holds fewer objects than the sold quantity, the key list stays authoritative and only the existing objects are deleted (never raising).

**D5 — Commands move objects and key deltas atomically; give transfers the receiver's key too.** `CmdGet`/`CmdDrop`/`CmdGive` resolve the object (search order: character containment first for drop/give, room contents for get), apply the matching key-list delta through `plan_inventory_delta` (add for get, remove for drop/give), and move the object in one `transaction.atomic()`. A refused move raises inside the transaction, so the database rolls back every completed move; the moved instances and the involved containers' contents caches are then reconciled with the rolled-back database (Evennia's idmapper keeps in-memory caches that a Django rollback cannot undo). When the canonical list holds a key but no contained object (key-only acquisition), 丟/給 first materializes the missing mirror object (in the room / at the target) and then transfers the key in the same transaction. `給` additionally adds the transferred keys to a character-like target's (PlayerCharacter or NPC) `db.inventory` in the same transaction, so the receiver's canonical list stays in sync. Unknown/non-registry objects still move as plain objects without key-list changes (documented behavior). Post-commit hooks (`at_get`/`at_drop`/`at_give`) run after the transfer as notification only.

**D6 — Command docs updated.** `docs/game/commands.md`/`command-reference.md` wording adjusted only where it describes the unified behavior.

## Risks / Trade-offs

- **Mixed object/key semantics for non-registry objects**: plain Evennia objects (e.g. future props) keep containment-only behavior; registry items are always key-listed. This is documented and matches the economy's ITEM_REGISTRY assumption.
- **Duplicate resolution**: object name search may match multiple objects; keep today's unambiguous-match requirement and reject ambiguous names.
- **Key-only acquisition divergence**: items granted by quest/guild/NPC-intent flows exist only as keys until the player first interacts via 拿/丟/給, which materializes the mirror; until then `db.inventory` remains authoritative and no drop/give is attempted on a phantom object.
- **Post-commit hook exceptions**: `at_get`/`at_drop`/`at_give` run after the atomic transfer as notifications; a hook exception surfaces as a command error while the transfer itself stays committed (pre-existing semantics, unchanged).
