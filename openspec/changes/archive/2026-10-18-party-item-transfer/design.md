# Design: Member item transfer rule and action

## Context

See proposal.md. Observed: `commands/localized/general.py::CmdGive` composes `plan_inventory_delta(caller, removals=...)` with a receiver plan and moves contained objects in one `transaction.atomic()` with surface snapshots; `plan_inventory_delta` already rejects guild property (`InventoryError`) and equipped removals (`EquippedRemovalError`). `preflight_equipment_toggle` reads `exam_restriction(entity)`. Combat activity is read through `world.rules.combat_session.is_in_active_session`.

## Goals / Non-Goals

**Goals:** one rules entry that the action (here) and the text commands (next change) share; deterministic rejection order; failure restores both bags.

**Non-Goals:** quest delivery advancement (stays with `交付` and non-member `給`), in-combat transfer, shared party inventory, affinity effects, companion wallets.

## Decisions

- **Rejection order** (first match wins, nothing written): `transfer_in_combat` (via `party_in_combat` over acting, commander, giver and receiver) → membership of giver then receiver (`not_party_member`, `member_not_present`) → `transfer_same_member` → quantity bounds (`invalid_quantity`) → unknown item (`item_not_held`) → `item_locked` → `item_not_held` (count) → `item_equipped` (count met only by equipped copies). Stable order makes the action and the text command report identically.
- **Composition**: preflight both plans (`plan_inventory_delta(giver, removals=...)`, `plan_inventory_delta(receiver, additions=...)`) before any write, then apply both inside one outer `transaction.atomic()` and move the contained mirror objects with quiet `move_to`; snapshot both members' `inventory`/quest-log surfaces and restore them on failure (same pattern as `CmdGive`). Alternative: reuse `CmdGive` code from the command module; rejected because rules must not import commands.
- **No time, no affinity, no delivery**: the rule never calls the clock, affinity or `advance_deliveries_for_transfer`.
- **Action**: `web/webclient/actions/party_actions.py` validates exactly four fields (ids positive safe integers, item key via the shared whitespace-free key validator, quantity 1..99), calls the rule with `session.puppet`, returns the fixed message 「你把 {n} 個{物品}交給了{成員}。」 and `affected_panels=()` (full snapshot). Possession does not refuse transfer.
- **Messages**: `transfer_in_combat` 「戰鬥中無法交換物品。」, `transfer_same_member` 「不能交給同一個人。」, `item_equipped` 「已裝備的物品無法交換；請先卸下。」, `item_locked` 「這件物品無法交換。」, `item_not_held` 「對方沒有足夠的這件物品。」, `invalid_quantity` 「數量不正確。」.

## Risks / Trade-offs

- [Delivery semantics diverge from legacy `給`] → Non-member targets keep the legacy path (next change); recorded as a planning gap.

## Migration Plan

Pre-release; revert the implementation commit. No stored-data migration.

## Verification and documentation ownership

EvenniaTest with synthetic items: success both directions, knocked-out receiver, every rejection in order with zero writes, injected failure after the giver write restoring both bags and contained objects, no tick or affinity change; action schema tests (extra field, bool id, whitespace key, quantity 0/100) and full-snapshot publication. Registry composition test updated. No player command changes here, so command docs wait for the next change. Observability lint, shard contract, `tools.contract_gate`.
