# Proposal: Shop window

## Why

Design §4.3 and §7 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the shop reuses the frame with 購買 and 出售 tabs and the shared member rail (recipient / seller), one price per view, the recipient's delta or held count per row, a current-versus-after comparison with delta chips for the other members, and an action bar with stepper, remaining purse and 買給 X. It replaces `ShopPanel`.

## What Changes

- New `ShopWindow.vue` on `WindowFrame` + `MemberRail` + `ListDetail` + `ActionBar` + `HoldingsStrip` (chips), rendering `services` v7 rows and `item_holdings`; selection through `party.view_member {tab: "shop", item_key}`; `shop.buy`/`shop.sell` with `recipient_id`/`seller_id`.
- Merchant navigation affordances (`surface: "shop"`) open the shop window.
- **BREAKING (pre-release)** delete `ShopPanel.vue`, its story `World/ShopPanel`, tests and `.elosern-root` duplicate rules.
- The purse rule admits exactly one balance per window plus the labelled remainder.

## Capabilities

### New Capabilities

- `webclient-shop-window`: the shop window contract.

### Modified Capabilities

- `webclient-contextual-hud`: the party purse requirement covers the shop window header and remainder.
- `webclient-component-showcase`: the services surfaces requirement names `ShopWindow`.
- `webclient-service-menus`: browser acceptance journeys use the shop window.

## Impact

- `web/webclient-app/components/ShopWindow.vue`, `AppClient.vue`, `composables/use-drawers.js`, intents, stories, manifest, Vitest; deletions above; one browser method.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **31 of 33**.

- depends-on: webclient-party-lineage-tab
- depends-on: services-shop-structured-rows

### Code and spec conflicts within the new batch

- `webclient-party-bag-retire`: shared showcase requirement "The map, art, and services surfaces…" and the purse requirement (S; that first, edits preserved; strict validation shows an informational archive-order notice for the renamed purse requirement).
- `services-shop-structured-rows`, `shop-party-recipient-seller`: last edited `ShopPanel.vue` (F; those first).
- `webclient-party-window-member-tab` and later tabs: shared `AppClient.vue`, manifest (F; ordered).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The `possessed_shop` refusal is unchanged.
