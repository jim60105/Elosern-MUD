# Design — realign-inventory-drawer-layout

## Context

The binding visual reference is `docs/design/elosern-redesign/index.html`
drawer `#dr-inv` (body sections at lines 957-986, `.doll`/`.dollslots`/`.itgrid`
CSS at lines 423-484). The current implementation is
`InventoryPanel.vue` (drawer body) + `EquipmentDoll.vue` (equipment section).
The committed payloads do not change: the `character` v4 panel's equipment rows
carry exactly `{slot, item_key, display_name}` and the `services` panel's
`inventory` section carries exactly `{rows, wallet}`. This is a template/CSS
restructure plus two new presentation blocks built from already-committed
values.

## Goals / Non-goals

- Goals: the 背包 drawer's DOM and section typography match the mock
  (`裝備`/`物品`/`金錢` `section.block`s, `.doll` flex row with a 裝備描述
  column, no panel-card wrapper); Storybook and the Vitest/browser suites
  assert the new structure.
- Non-goals: the mock's `排序/篩選/找尋` pill row (prohibited by the main
  spec — see delta), drawer chrome changes (head icon, 46px top clearance →
  `align-drawer-chrome-symbols`), the `.dock-menu-layout` removal (→
  `remove-redundant-dock-menu-layout`), any payload/protocol change.

## Decisions

### D1 — `.doll` becomes a flex row inside `EquipmentDoll.vue` (no new component)

`EquipmentDoll.vue`'s root `section.equipment-doll` keeps its identity and all
existing `data-testid`s. Its available-state template becomes:

```
<div class="equipment-doll__doll">            <!-- mock: .doll -->
  <div class="equipment-doll__slots">…</div>  <!-- mock: .dollslots (unchanged) -->
  <div class="equipment-doll__description"    <!-- mock: the flex:1 裝備描述 div -->
       data-testid="equipment-doll__description">…</div>
</div>
<section class="equipment-doll__section">…duplicate/other-slot rows…</section>
```

- `__doll`: `display:flex; gap:12px; align-items:flex-start` (mock `.doll`).
- `__slots`: unchanged 2x74px grid (mock `.dollslots`).
- `__description`: `flex:1; min-width:0` and renders one labelled line per
  committed row grouped by slot label (`主手 · 短劍 · 拾遺`), plus the retained
  accessory group; `overflow-wrap:break-word`. Slot captions stay in the grid;
  the per-slot `__slot-item` name line under each box is removed (it moves to
  the description column). Duplicate/other-slot fallback rows stay full-width
  under the row, exactly as today (they keep their labelled no-drop guarantee).
- Alternative rejected: extracting `EquipmentDescription.vue` — it would need a
  new frozen-manifest story title for no benefit; the doll owns the data.

### D2 — Section headings replace the `裝備人偶` h3

`EquipmentDoll.vue` renders the mock's `h4`-style label (`font-size:11px`,
`letter-spacing:.14em`, `color:var(--paper-500)`, tag `margin-left:auto` in
`--paper-700`): heading text `裝備`, tag `真值 · 偽裝不影響`. The heading element
keeps `data-testid="equipment-doll__title"` (semantic level becomes `h3` for
drawer outline correctness is acceptable; only its text changes from
`裝備人偶` to `裝備`). No test pins the old string (verified).

### D3 — `InventoryPanel.vue` becomes the three-section stack

- Remove `.inventory-panel`'s `background/border/border-radius` (mock body is
  transparent) and keep the aside as a plain column with 18px section rhythm.
- `物品` section: heading with tag = `rows.length` (shipped listing size; the
  ceiling sentence already prevents misreading it as a total) + the unchanged
  grid + unchanged ceiling note.
- `金錢` section: one mock `.statrow`-styled row (`--ink-820` background,
  `--ink-700` border, label `錢袋` + small `整數銅`, value grouped mono gold).
  Wallet source: the committed `character.wallet` integer — the exact value the
  head subtitle already renders (passed in as an optional `wallet` prop from
  `AppClient`, which owns that computed subtitle; `services.inventory.wallet`
  is deliberately NOT used for the row so head and body can never disagree).
  Rendered only when the value is a committed non-negative integer; absent
  otherwise (no zero-balance fabrication).
- New testids: `inventory-panel__section--items`,
  `inventory-panel__items-count`, `inventory-panel__section--wallet`,
  `inventory-panel__wallet-value`. All existing testids are preserved.

### D4 — Storybook stays in the frozen manifest

Only new named exports in the two existing story files
(`WithEquipmentDescription`, `WalletSection` states ride on the existing drawer
wrapper). `npm run showcase-coverage` must stay green; `Data/EquipmentDoll` and
`World/InventoryPanel` titles are untouched.

## Risks / trade-offs

- Managed browser tests (`test_browser_inventory_grid.py`,
  `test_browser_contextual_hud.py`) traverse the bag DOM; they must be updated
  in the same change or CI shard breaks. Mitigation: run the single
  `test_browser_inventory_grid.py` class locally (within the 5-minute budget)
  and search for `equipment-doll__slot-item` / old-order assumptions.
- The `物品` count tag could be read as a total; mitigation is the unchanged
  ceiling wording plus the delta's explicit listing-size wording.
- Removing the per-slot item name under the box slightly lengthens visual
  distance between a slot and its name; the mock accepted the same trade-off,
  and the a11y slot caption + description column keep the pairing programmatic
  (`equipment-doll__description-row--<slot>` testids).
