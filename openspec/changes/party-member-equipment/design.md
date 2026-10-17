# Design: Equipment toggle for any present member

## Context

See proposal.md. `preflight_equipment_toggle(entity, item_key)` and `toggle_equipment(entity, item_key)` already operate on any entity's own `db.inventory`/`db.equipment`, sync gauge limits and move attached buffs atomically. `_inventory_toggle_equip_adapter(actor, payload)` toggles the puppet; combat drafts are preflighted against current state at submission (party-combat atomic rounds), so no explicit invalidation hook exists.

## Goals / Non-Goals

**Goals:** member-scoped toggle for every present member, in and out of combat, text and action parity.

**Non-Goals:** cross-member equipping (equipping an item another member holds needs a transfer first), any new slot rule, any affinity effect.

## Decisions

- **Member boundary first**, then the unchanged toggle. Organizing purpose admits a knocked-out member (design §4.1 reasoning applies: reorganizing gear is not acting).
- **Combat presence** uses the same room check; a companion in combat stands in the commander's room, so no combat-session lookup is needed for authorization.
- **Messages** keep the existing toggle sentences with the subject replaced by the member's name when the member is not the caller: 「艾拉 裝備了 樺木法杖。」 / 「艾拉 卸下了 樺木法杖。」.
- **Transitional client**: until the bag tab lands, `InventoryPanel` sends the controlled figure's id; no hidden default exists on the server (the field is required).

## Risks / Trade-offs

- [A stale client omits `actor_id`] → Exact-schema rejection; the bundled client ships in the same change.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

EvenniaTest: companion equip/unequip/replace in exploration and during an active session (no round/time), knocked-out companion admitted, absent/non-member rejected without commander substitution, saved draft entry preflighted after the toggle. Action schema tests; Vitest for the drawer payload. Update both command documents and run `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
