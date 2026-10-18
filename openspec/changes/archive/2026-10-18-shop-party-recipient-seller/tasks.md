# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Economy rule (3h)

- [x] 1.1 Change `buy`/`sell` to take the recipient/seller, pay from and to the commander purse, keep prices, affinity and stock rules, and snapshot both members' surfaces; verify independent arithmetic for companion and commander recipients, forged and absent members, insufficient funds, the existing `equipped_item` refusal on sell, stock cap, and an injected failure restoring purse, both wallets, both bags, quest log, claims and stock.

## 2. Actions and transitional client (1.5h)

- [x] 2.1 Make `shop.buy` exactly `{item_key, quantity, recipient_id}` and `shop.sell` exactly `{item_key, quantity, seller_id}`, keep the `possessed_shop` refusal first; send the controlled figure from `ShopPanel.vue`; verify service action schema/adapter tests and the Vitest shop payload.

## 3. Text commands and documentation (1.5h)

- [x] 3.1 Add `= <成員>` and the `買`/`賣` aliases to `CmdBuy`/`CmdSell`; verify parity with the actions and refusal messages; update both player command documents and run `tests/test_command_docs.py`.

## 4. Integration (1h)

- [x] 4.1 Pin the observed ACQUIRE behaviour for a companion recipient in a test, annotate canonical IDs for the added `shop-economy` requirements and the modified `webclient-service-menus` requirement, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate shop-party-recipient-seller --strict`. (The three added requirements' own IDs are indexed only after archival synchronization, so the annotations name the current canonical requirements the behaviour establishes and the new IDs are recorded in the test class docstring; annotating an unindexed ID would fail `tools.spec_traceability check` as `unknown-requirement-id`.)
