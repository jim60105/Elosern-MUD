# Design: party_inventory panel

## Context

See proposal.md. `world/rules/service_view.py` builds the puppet's `InventorySectionView` rows (held count, equipped flag, presentation, one action) for `services.inventory`; `preflight_equipment_toggle(entity, key)` returns allowed/reason; item use has a side-effect-free preflight; `enumerate_actor_item_choices` provides combat-usable options per actor.

## Goals / Non-Goals

**Goals:** member-scoped rows with all three descriptors; truthful combat behaviour; no client arithmetic.

**Non-Goals:** the holdings strip (`item-holdings-panel`), removing `services.inventory`, any UI.

## Decisions

- **Rules view** `inventory_view(member, *, in_combat)` groups canonical keys into rows (held, equipped count, slot), and for each row computes: `toggle` from `preflight_equipment_toggle(member, key)` (null for non-equipment); `use` in exploration from the item-use preflight for the member (null for non-usable), in combat from the member's combat item choices (descriptor `route: "combat_draft"`, enabled when the member is a commandable actor with that item available); `give` from the transfer preflight with the giver = member and quantity 1 (`max_quantity` = unequipped copies; disabled with `transfer_in_combat` in combat).
- **Descriptor shape** `{route, enabled, reason}` where `route` ∈ `field_use`, `combat_draft`, `toggle`; `give` is `{enabled, reason, max_quantity}`. Messages are the rules' fixed texts.
- **Presentation** reuses the existing item presentation metadata serializer from `services.py`.
- **Bounds**: rows ≤ the existing inventory row ceiling; maximal fixture within the byte bound.

## Risks / Trade-offs

- [Duplicate row logic with `service_view`] → Acceptable during transition; `services-shop-structured-rows` deletes the services inventory section and its view.

## Migration Plan

Pre-release additive; revert the implementation commit.

## Verification and documentation ownership

Rules view tests (equipped give refusal, combat give refusal, combat draft use enabled for a commandable companion and disabled for a knocked-out one, toggle reasons), presenter tests (companion subject, possession-identical, malformed storage unavailable, maximal bound), mirror parity, allowlist contract. No command changes. Shard registration; `tools.contract_gate`.
