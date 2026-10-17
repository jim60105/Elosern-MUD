# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Shop window (3h)

- [ ] 1.1 Implement `ShopWindow.vue` (tabs, shared rail, rows, comparison, chips, action bar) and route merchant affordances to it; verify Vitest selection carry-over, `shop.buy`/`shop.sell` payloads with member ids, one price per view, per-row delta or held count, chips from `item_holdings`, stepper bounds, labelled remaining purse, closed-shop reasons and the possession refusal message.

## 2. Deletion and stories (1.5h)

- [ ] 2.1 Delete `ShopPanel.vue`, its story, manifest title, tests and duplicate `.elosern-root` rules; add shop stories (buy equipment, sell) at both sizes; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 3. Browser evidence and integration (2.5h)

- [ ] 3.1 Add one browser method buying potions for a companion, registered in `.github/browser-shards.json`; update `web/webclient-app/AGENTS.md`; annotate canonical IDs for the added and modified requirements; run the touched Vitest files, `tests.test_evennia_test_optimization_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-shop-window --strict`.
