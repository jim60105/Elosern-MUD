# Design: Party window 背包 tab (browse, give, use, equip)

## Context

See proposal.md. The prototype `tabs/BagTab.vue` defines the doll above the rows, the detail ribbon, the holdings strip and the action bar. `party_inventory` and `item_holdings` carry every fact the tab renders.

## Goals / Non-Goals

**Goals:** a complete exploration bag tab for any member from committed panels only.

**Non-Goals:** combat routing and component deletion (`webclient-party-bag-retire`), shop comparison (shop window).

## Decisions

- **Item selection is server state** through `party.view_member {member_id, tab: "bag", skill_key: null, item_key}`; the detail waits for `item_holdings` for that key and shows the committed unavailable reason otherwise.
- **Stepper** bounds: 1..`give.max_quantity`, forced to 1 for equipment rows; the quantity resets when the viewed member or item changes.
- **Use** keeps the existing labelled confirmation dialog pattern inside the window.
- **Equip label** names the replaced singleton occupant from `party_inventory.equipment`, never a client-chosen accessory.

## Risks / Trade-offs

- [Two bag surfaces coexist for one change] → Unreleased cutover; the retire change removes the old one.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

Vitest: slot filter, item-selection payload, holdings without invention, stepper bounds, `party.transfer` payload, disabled receive reason, use confirmation, equip label, possession-identical rendering. Stories (consumable, equipment) at both sizes; Storybook build and showcase coverage. `tools.contract_gate`.
