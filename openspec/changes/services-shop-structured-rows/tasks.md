# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Service view (2.5h)

- [ ] 1.1 Remove the inventory section from `service_view.py` and build stock/sellable facts for the viewed member (held, delta via `equipment_delta`, unequipped sellable counts, purse-based enablement); verify service view tests for each fact and the not-equippable reason.

## 2. services v7 schema (2h)

- [ ] 2.1 Bump `services.py` to v7 (no inventory, `member_id`, presentation, `viewed`, single price per row kind, pagination without `inventory_total`), add `services` to the `party.view_member` affected panels, update the JS mirror, parity contract and fixtures; verify presenter/validator/mirror tests and the maximal bound.

## 3. Transitional client and integration (2h)

- [ ] 3.1 Update `ShopPanel.vue` to the v7 rows and to send `services.shop.member_id` as recipient/seller and verify Vitest ShopPanel and QuestDrawer; annotate canonical IDs for the two modified `webclient-service-menus` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate services-shop-structured-rows --strict`.
