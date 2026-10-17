# Design: Item holdings query panel

## Context

See proposal.md. `preflight_equipment_toggle(entity, key)` computes the before/after mapping but requires the member to hold the item; `build_character_read_model(entity)` computes breakdown trait values from canonical equipment; `party.view_member` stores `(member_id, tab)` per session (change 13).

## Goals / Non-Goals

**Goals:** one bounded, write-free holdings answer for the selected item, shared by the bag and the shop.

**Non-Goals:** whole-bag holdings (exceeds the envelope), any UI, stock-row deltas (shop change).

## Decisions

- **Hypothetical swap**: `equipment_delta(member, key)` resolves the item's slot, builds the after mapping exactly as the toggle would (singleton replace or accessory append), and rejects with the toggle's stable reason (`guild_property`, `exam_kit_locked`, `accessory_slots_full`, `not_equipment`) without the ownership check, so a member who does not hold the item still gets a delta. Effective traits are computed by the breakdown read model with an injected equipment mapping (a read-only parameter added to the read model), and only nonzero changes are listed in the canonical trait order.
- **receive** uses the transfer preflight (giver = viewed member, receiver = row member, quantity 1); the giver's own row is disabled with no reason.
- **Selection**: `party.view_member` stores `item_key` (validated as a bounded key; an unknown registry key stores null). Changing tabs keeps the item only when the client resends it.
- **Bounds**: ≤ 17 rows, ≤ 16 changes per row; maximal fixture within the byte bound.

## Risks / Trade-offs

- [Injecting an equipment mapping into the read model] → A keyword-only parameter defaulting to canonical storage; a test proves the default path is byte-identical.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

Independent arithmetic: synthetic sword attack +6 vs. staff +0 → +6; vs. warhammer +10 → −4; accessory append when slots free; full accessory slots → not equippable with reason; non-equipment null delta; combat counts with receive disabled; absent member receive refusal; write-free snapshot. Presenter/mirror parity; action schema with `item_key`. `tools.contract_gate`.
