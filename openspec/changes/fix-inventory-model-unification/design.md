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

**D1 — Canonical record = `db.inventory` key list (registry items).** All reads (`背包`, sell, ACQUIRE, turn-in) continue to read the list; object containment is a mirror for command UX. Non-registry Evennia objects are containment-only by design and never enter the key list.

**D2 — Every registry item has a contained object; commands move both.** `buy` materializes (or reuses) the corresponding Evennia Object in the character's containment inside the same transaction that writes the key list, so drop/give always have a real object to move. `CmdGet`/`CmdDrop`/`CmdGive` resolve the object (search order: character containment first for drop/give, room contents for get), apply the matching key-list delta through `plan_inventory_delta` (add for get, remove for drop/give), and move the object in one `transaction.atomic()` with snapshot/restore. Unknown/non-registry objects still move as plain objects without key-list changes (documented behavior).

**D3 — Command docs updated.** `docs/game/commands.md`/`command-reference.md` wording adjusted only where it describes the unified behavior.

## Risks / Trade-offs

- **Mixed object/key semantics for non-registry objects**: plain Evennia objects (e.g. future props) keep containment-only behavior; registry items are always key-listed. This is documented and matches the economy's ITEM_REGISTRY assumption.
- **Duplicate resolution**: object name search may match multiple objects; keep today's unambiguous-match requirement and reject ambiguous names.
