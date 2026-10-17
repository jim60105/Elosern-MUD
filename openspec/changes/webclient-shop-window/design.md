# Design: Shop window

## Context

See proposal.md. `ShopPanel.vue` renders `services.shop` stock/sellable rows with a quantity form; the prototype `ShopPrototype.vue` defines the window.

## Goals / Non-Goals

**Goals:** a complete shop window for any recipient/seller with one price per view and server facts only.

**Non-Goals:** restyling other service windows (design §13), price rules.

## Decisions

- **Shared selection**: the rail reads `party.viewed_member_id`; selecting dispatches `party.view_member {member_id, tab: "shop", skill_key: null, item_key}` so `services.shop.member_id` and `item_holdings` follow.
- **Row facts** come from `viewed` (recipient) and the chips from `item_holdings` rows (other members); the comparison panel shows the recipient's delta changes only (server), never recomputed.
- **Remaining purse** = header purse minus price × quantity, a display-only preview labelled as remaining; the server's result is authoritative.
- **Stepper** bounds from the committed buy/sell descriptor quantity maximum.

## Risks / Trade-offs

- [Display arithmetic for the remainder] → Limited to one subtraction of committed integers; the result alert and next snapshot remain authoritative.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: selection carry-over from the party window, buy/sell payloads with member ids, one price per view, delta/held per row, chips from holdings, stepper bounds, remaining purse label, possession refusal surfaced, closed-shop reasons, no rule prose. Stories (buy equipment, sell) at both sizes; Storybook build and showcase coverage; one browser method (buy potions for a companion) in `.github/browser-shards.json`; AGENTS.md. `tools.contract_gate`.
