# Design: services v7 structured shop rows

## Context

See proposal.md. `service_view.build_services_view(actor)` builds host, player, guild, shop (stock with both prices, sellable from the actor's bag) and inventory sections; `services.py` validates v6 including `MAX_INVENTORY_ROWS` and pagination totals; the presentation serializer for rows already exists for inventory rows.

## Goals / Non-Goals

**Goals:** exact v7 rows for the viewed member; no inventory duplication with `party_inventory`; one price per view.

**Non-Goals:** the shop window UI, price formulas (unchanged), possession rules (the `possessed_shop` refusal stays in the actions).

## Decisions

- **Viewed member** comes from the copied selection (`resolve_viewed_member`), used only for `viewed` facts, sellable rows and enablement; host resolution stays on the acting puppet's room.
- **viewed.held** counts the member's canonical copies; **viewed.delta** is `equipment_delta(member, key)` for equipment and null otherwise; the shop never computes deltas for other members (the shop window uses `item_holdings` for the chips).
- **Enablement**: buy uses the economy preflight with the commander purse and the viewed member as recipient; sell uses the viewed member's unequipped count.
- **Bounds**: stock/sellable ≤ 12 rows each; maximal fixture within the byte bound.

## Risks / Trade-offs

- [QuestDrawer reads `services`] → It reads guild sections only; a Vitest regression run covers it.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Presenter tests: removed inventory section, one price per row kind, `viewed.held`, equipment delta for the viewed member, not-equippable reason, sellable unequipped count, purse-based buy enablement, possession payload identical; validator/mirror parity and bounds; Vitest ShopPanel and QuestDrawer. No command changes. `tools.contract_gate`.
