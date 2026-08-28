# Tasks — realign-inventory-drawer-layout

## 1. Equipment doll (`.doll` row + 裝備 heading)

- [x] 1.1 In `EquipmentDoll.vue`, wrap the slot grid in a new
  `.equipment-doll__doll` flex row (`gap:12px; align-items:flex-start`) and add
  the `equipment-doll__description` column (`flex:1`) that renders one
  `equipment-doll__description-row--<slot>` entry per committed row (slot label
  + committed `display_name`), the accessory group under its slot label, and
  the unchanged empty statement when no row is committed.
- [x] 1.2 Remove the per-slot `.equipment-doll__slot-item` name line (the name
  now lives in the description column); keep slot captions, icons, dashed
  empty states, duplicate/other-slot fallback sections, and every existing
  `data-testid`.
- [x] 1.3 Change the title element's text from `裝備人偶` to `裝備` and restyle
  it as the mock's tracked section heading with the right-aligned tag
  `真值 · 偽裝不影響` (keep `data-testid="equipment-doll__title"`).

## 2. Bag sections (物品 / 金錢 / no wrapper card)

- [x] 2.1 In `InventoryPanel.vue`, drop the `.inventory-panel`
  `background/border/border-radius` wrapper styling and introduce the mock's
  `section.block` stack: the doll section, an `物品` heading section tagged
  with the shipped row count (`inventory-panel__items-count`), and a `金錢`
   section (`inventory-panel__section--wallet`) with one `.statrow`-styled row
   showing the grouped integer wallet (`inventory-panel__wallet-value`) from
   the committed `character.wallet` integer passed in from `AppClient` as an
   optional `wallet` prop (never `services.inventory.wallet`, so head and body
   can never disagree); render the wallet row only when that prop carries a
   committed non-negative integer. Wire the prop in `AppClient.vue` from the
   same validated character-panel value the head subtitle uses.
- [x] 2.2 Keep the tile grid, ceiling note, inspector, selection/a11y behavior,
  and all existing testids byte-identical; do not add the mock's
  排序/篩選/找尋 pills.

## 3. Tests with the behavior

- [x] 3.1 Update `web/webclient-app/tests/data/equipment_doll.test.js`:
  description-column grouping (incl. accessory group, unrecognised slot,
  duplicate rows) and `裝備人偶` absence / `裝備` + tag presence.
- [x] 3.1a Re-express the wallet-singleton contract:
  `web/webclient-app/tests/app_client_drawers.test.js:72` now asserts the
  wallet renders exactly in the inventory drawer's subtitle and its `金錢`
  row (same figure) and zero times in every other drawer; extend its evidence
  wrapper `web/webclient/tests/test_vue_hud_drawer_evidence.py`
  (`test_drawer_layer_single_wallet`, literal ID
  `webclient-contextual-hud::the-drawer-layer-renders-the-wallet-exactly-once`
  — confirm via `uv run --locked python -m tools.spec_traceability list`) to
  name the two locations. Extend the bag/doll requirement evidence in
  `web/webclient/tests/test_vue_hud_drawer_evidence.py:84-114` and
  `web/tests/browser/test_browser_inventory_grid.py:45-49` with the new
  structural assertions, reusing their literal IDs — no new IDs. Run
  `uv run --locked python -m tools.spec_traceability check`.
- [x] 3.2 Update `web/webclient-app/tests/world/inventory_panel.test.js`:
  three-section order, items tag = shipped count, wallet row formatting and
  absence rules (unavailable services / unavailable character / non-integer
  wallet), and no sort/filter/search pill; run the Vitest files with
  `npm test`.
- [x] 3.3 Update managed browser evidence: add assertions for the equipment
  description column and the 金錢 row to
  `web/tests/browser/test_browser_inventory_grid.py`, and fix any
  `equipment-doll__slot-item`/structure assumptions in
  `web/tests/browser/test_browser_contextual_hud.py`; run the single
  `test_browser_inventory_grid.py` class locally.

## 4. Showcase alignment

- [x] 4.1 Add variant exports to `stories/Data/EquipmentDoll.stories.js`
  (`WithEquipmentDescription`, long-label and empty variants) and
  `stories/World/InventoryPanel.stories.js` (equipment + wallet section
  states), each `args`-bound; keep the existing story titles so the frozen
  manifest is untouched.
- [x] 4.2 Run `npm run showcase-coverage` and `npm run build-storybook`; verify
  the drawer visually in the built showcase against
  `docs/design/elosern-redesign/index.html` (agent-browser screenshots of both
  `#dr-inv` and the Storybook iframe).

## 5. Gates

- [x] 5.1 `openspec validate realign-inventory-drawer-layout --strict`.
- [x] 5.2 `uv run --locked python -m tools.spec_traceability check`; `git diff
  --check` clean.
