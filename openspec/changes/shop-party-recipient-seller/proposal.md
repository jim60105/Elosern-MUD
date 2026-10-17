# Proposal: Shop recipient, seller and party purse

## Why

Design §3.2, §4.3 and §7 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: `shop.buy` carries a recipient and `shop.sell` a seller; the price is paid from and proceeds go to the party purse, which is the commander's `db.wallet`. Today `world/rules/economy.py::buy/sell(actor, ...)` uses the puppet's wallet and bag.

## What Changes

- `buy(acting, merchant_host, item_key, quantity, recipient)` and `sell(acting, merchant_host, item_key, quantity, seller)`: the member boundary (organizing purpose) re-derives the recipient or seller; the purse is `resolve_commander(acting).db.wallet`; buy and sell prices are unchanged (sell is half of buy); merchant affinity stays with the commander; all writes stay in the existing single transaction with snapshot/restore extended to the member's bag.
- **BREAKING (pre-release)** `shop.buy` payload `{item_key, quantity, recipient_id}`; `shop.sell` payload `{item_key, quantity, seller_id}`. The possessed refusal (`possessed_shop`) is unchanged.
- Text: `buy`/`sell` accept `= <成員>`; new aliases `買` and `賣` matching the design's command table. Both player command documents updated.
- The current `ShopPanel` sends the controlled figure as recipient/seller until the shop window lands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shop-economy`: recipient/seller/purse requirements, possession refusal retained, text syntax.
- `webclient-service-menus`: the service-action allowlist admits `recipient_id` and `seller_id`.

## Impact

- `world/rules/economy.py`, `web/webclient/actions/service_actions.py`, `commands/economy.py`, `web/webclient-app/components/ShopPanel.vue` and its intent wiring.
- Docs: both player command documents.
- Tests: `world/rules/tests/test_economy.py` (or the existing economy test module) extended, service action tests, command tests, Vitest shop payload.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **11 of 30**.

- depends-on: party-member-authority
- depends-on: party-practice-booking

### Code and spec conflicts within the new batch

- `party-member-equipment`, `companion-field-item-use`: shared spec requirement `webclient-service-menus` "Service actions are exact, allowlisted, and server-authoritative" (S; this delta is last and preserves both `actor_id` fields); shared file `service_actions.py` (F).
- `party-practice-booking` and earlier text-command changes: shared command docs (F; ordered, hence the declared prerequisite).
- `services-shop-structured-rows`: consumes the recipient/seller semantics for row facts (D) and shares `ShopPanel.vue` (F).
- `webclient-shop-window`: removes `ShopPanel.vue` (F; ordered).

### Active change coordination

No active OpenSpec change. Possession rules unchanged.
