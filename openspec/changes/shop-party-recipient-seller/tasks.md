# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Economy rule (3h)

- [ ] 1.1 Change `buy`/`sell` to take the recipient/seller, pay from and to the commander purse, keep prices, affinity and stock rules, and snapshot both members' surfaces; verify independent arithmetic for companion and commander recipients, forged and absent members, insufficient funds, `item_equipped` on sell, stock cap, and an injected failure restoring purse, both bags, quest log and stock.

## 2. Actions and transitional client (1.5h)

- [ ] 2.1 Make `shop.buy` exactly `{item_key, quantity, recipient_id}` and `shop.sell` exactly `{item_key, quantity, seller_id}`, keep the `possessed_shop` refusal first; send the controlled figure from `ShopPanel.vue`; verify service action schema/adapter tests and the Vitest shop payload.

## 3. Text commands and documentation (1.5h)

- [ ] 3.1 Add `= <成員>` and the `買`/`賣` aliases to `CmdBuy`/`CmdSell`; verify parity with the actions and refusal messages; update both player command documents and run `tests/test_command_docs.py`.

## 4. Integration (1h)

- [ ] 4.1 Pin the observed ACQUIRE behaviour for a companion recipient in a test, annotate canonical IDs for the added `shop-economy` requirements and the modified `webclient-service-menus` requirement, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate shop-party-recipient-seller --strict`.
