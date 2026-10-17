# Design: Shop recipient, seller and party purse

## Context

See proposal.md. `buy` validates quantity, registry, sellability, local merchant, offer, open hours, stock and wallet, then plans `plan_inventory_delta(actor, additions=...)`, writes wallet/inventory/quest-log/stock/affinity/mirror objects in one `transaction.atomic()` with `_snapshot_trade` / `_restore_trade`. `sell` is symmetric. The adapters refuse a possessed puppet with `possessed_shop`.

## Goals / Non-Goals

**Goals:** member-scoped bag, commander purse, unchanged prices and refusals, text/action parity.

**Non-Goals:** structured stock rows and per-member deltas (`services-shop-structured-rows`), the shop window (`webclient-shop-window`), companion wallets.

## Decisions

- **Signature** `buy(acting, merchant_host, item_key, quantity, recipient)`: membership is checked first (so a forged id never reaches pricing), then the existing checks in their existing order; the wallet read/write targets the commander; the inventory plan and mirror objects target the recipient. `_snapshot_trade` captures the commander's wallet and the member's inventory and quest log.
- **Sell eligibility** reuses `plan_inventory_delta(seller, removals=...)`, which already raises `EquippedRemovalError` for equipped copies; it maps to `item_equipped` instead of the generic insufficient reason.
- **Affinity** (`AffinitySource.TRADE`) stays between the merchant host and the commander, because the commander pays; recorded explicitly so it is not changed accidentally.
- **ACQUIRE progress** follows the existing planner for the recipient; the observed effect of buying into a companion's bag on the commander's ACQUIRE objectives is pinned by a test and listed as a planning gap.
- **Aliases** `買`/`賣` are added because the design's text table uses them; existing keys and aliases remain.

## Risks / Trade-offs

- [Two members' surfaces in one trade] → One snapshot covers both; injected failure tests prove restoration.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

EvenniaTest with independent arithmetic (purse 1,240 − 3×40 = 1,120; sell 2×10 = +20 when buy is 20): companion recipient, commander recipient, forged/absent member, insufficient funds, equipped sell refusal, stock cap, possession refusal, injected failure restoring purse, both bags and stock. Action schema tests, command parity, Vitest shop payload. Both command documents; `tests/test_command_docs.py`; shard contract; `tools.contract_gate`.
