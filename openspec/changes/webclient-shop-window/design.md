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
- **Comparison without a committed slot**: a stock row carries no equipment slot, so the window never names the replaced occupant (that would infer a slot). The 目前 box lists the recipient's committed effective values for the traits the server delta changes (from the `character` panel, only while it names the recipient); the 換上後變化 box lists the item and the server delta lines verbatim. No after value is added up.
- **Trade republishes the bag**: `shop.buy`/`shop.sell` add `party_inventory` to their affected panels so the party window's 背包 tab and header purse match the trade (the viewed member's panel; the window disables trades while the rail and `shop.member_id` disagree).
- **無法裝備 codes stay data**: the delta's stable reason code is carried as `data-reason-code`, never shown as text, in the shop rows, chips and `HoldingsStrip`.

## Risks / Trade-offs

- [Display arithmetic for the remainder] → Limited to one subtraction of committed integers; the result alert and next snapshot remain authoritative.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: selection carry-over from the party window, buy/sell payloads with member ids, one price per view, delta/held per row, chips from holdings, stepper bounds, remaining purse label, possession refusal surfaced, closed-shop reasons, no rule prose. Stories (buy equipment, sell) at both sizes; Storybook build and showcase coverage; one browser method (buy potions for a companion) in `.github/browser-shards.json`; AGENTS.md. `tools.contract_gate`.
