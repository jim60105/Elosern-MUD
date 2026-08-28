# Realign the 背包 drawer layout with the v2 redesign

## Why

`docs/design/elosern-redesign/index.html` (drawer `#dr-inv`, lines 957-986) is the
visual source of truth agreed in the HUD redesign roadmap, but the shipped
`背包 · 裝備` drawer diverges from it in structure, not just cosmetics. A
side-by-side DOM comparison (agent-browser against the Storybook surface and the
redesign mock) found:

| # | Redesign (`#dr-inv`) | Current implementation | Gap |
|---|---|---|---|
| 1 | `.doll` is a flex row whose children are `.dollslots` (2x74px grid) **plus a second `div` (flex:1) carrying the 裝備描述** (equipped summary beside the slot grid) | No `.doll` flex row at all: `.equipment-doll` is a `flex-direction: column` stack, the slots grid stands alone, and item names hang under each slot caption; there is no description column | structure |
| 2 | `.equipment-doll`-equivalent layout is `display:flex; gap:12px; align-items:flex-start` with a 14px section bottom margin | `.equipment-doll` is a vertical flex column; the whole equipment block is full width | layout |
| 3 | The equipment section is introduced by a small tracked section heading `裝備` + right-aligned tag `真值 · 偽裝不影響` (`.block h4`) | The block is titled with an `h3` reading `裝備人偶` | title/typography |
| 4 | `物品` is a `section.block` with an `h4` heading (`物品` + count tag) and `金錢` is its own `section.block` with a `.statrow` (錢袋 / integer copper) | Neither section exists: the tile grid floats directly in the drawer body with no heading, and the wallet appears **only** in the drawer head subtitle; the whole body is additionally wrapped in a bordered `--panel` card the mock does not have | sections |
| 5 | Sections sit directly on the transparent drawer body | `.inventory-panel` paints its own `background: var(--panel); border; border-radius` box inside the drawer body | chrome |

The remaining redesign surfaces (dock, HUD islands, drawers) are aligned closely
enough to be handled by their own small changes (see Related changes); this
change is scoped to the 背包 panel so it lands in one workday.

The mock's 物品 pill row (`排序：近期 / 篩選：全部 / 找尋`) is **deliberately not
copied**: the `webclient-contextual-hud` main spec forbids the bag from
rendering sorting/filtering/search controls, and the mock's pills are decoration
with no backing data. Truthful-data scope wins over pixel parity for that one
row.

## What Changes

- Restructure `EquipmentDoll.vue` to the mock's `.doll` DOM: a flex row
  (`gap: 12px; align-items: flex-start`) containing (a) the existing two-column
  74px slot grid (identical slot roles, icons, dashed empty states, overflow and
  passthrough rules — all preserved) and (b) a new right-hand 裝備描述 column
  (`flex: 1`) that lists the committed equipment rows grouped by slot label
  (e.g. `主手 · 短劍 · 拾遺`, `盔甲 · 皮甲`, `飾品 · N 件`). The column renders
  only committed `display_name` values; no statistic, rarity, or summary is
  invented (the equipment rows carry none).
- Replace the `裝備人偶` `h3` with the mock's section-heading treatment: the
  heading reads `裝備` and carries the right-aligned tag `真值 · 偽裝不影響`
  (11px, `letter-spacing .14em`, `--paper-500`, tag in `--paper-700`) shared by
  the other bag sections.
- Give `InventoryPanel.vue` the mock's `section.block` stack: `裝備` (the doll),
  `物品` (h4 + shipped-count tag + the existing tile grid + the existing
  ceiling note), and `金錢` (a `.statrow`-styled row: `錢袋 整數銅` label,
  grouped integer copper value — the same committed `character.wallet` figure the
  head subtitle renders, passed in as a prop). Remove the
  bordered `--panel` card wrapper so sections sit on the transparent drawer body
  like the mock's `.draw .body`.
- Keep every existing `data-testid`, the head subtitle, tile/inspector behavior,
  a11y guarantees, and all current spec prohibitions (no stats, no sort/filter/
  search control, no fabricated totals).
- Update the `Data/EquipmentDoll` and `World/InventoryPanel` Storybook stories
  with states for the description column (empty equipment, one accessory, long
  labels) and the 金錢 section, keeping the frozen `component-manifest.json`
  titles unchanged (variant exports only).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - Requirement `The drawer layer renders the wallet exactly once` — the
    inventory drawer may render the wallet twice per opening (head subtitle +
    its `金錢` section row, one committed source); every other drawer and every
    other inventory body element still renders zero balances.
  - Requirement `The bag renders the bounded inventory rows without inventing a
    total or a rarity` — the wallet additionally renders in exactly one `金錢`
    section row (replacing "no other body location"); the body is a
    `section.block` stack with `物品`/`金錢` headings and no panel-card wrapper.
    Sort/filter/search remains prohibited.
  - Requirement `The equipment doll renders only server-authored slots and drops
    nothing` — the doll becomes the mock's `.doll` flex row: slot grid plus a
    beside-slot 裝備描述 column; the section heading reads `裝備` (not
    `裝備人偶`) with the `真值 · 偽裝不影響` tag; slot/overflow/passthrough and
    no-statistics guarantees are unchanged.

## Impact

- Code: `web/webclient-app/components/EquipmentDoll.vue`,
  `web/webclient-app/components/InventoryPanel.vue` (template + scoped CSS only;
  no store/protocol/payload changes).
- Showcase: `web/webclient-app/stories/Data/EquipmentDoll.stories.js`,
  `web/webclient-app/stories/World/InventoryPanel.stories.js` (new variant
  exports; no new story titles, so the frozen manifest gate stays green).
- Tests: `web/webclient-app/tests/data/equipment_doll.test.js`,
  `web/webclient-app/tests/world/inventory_panel.test.js`,
  `web/webclient-app/tests/app_client_drawers.test.js` — the
  `renders the wallet exactly once across the whole drawer layer` test (line
  72) is re-expressed as the two-places-in-one-drawer rule (its evidence
  wrapper `web/webclient/tests/test_vue_hud_drawer_evidence.py::test_drawer_layer_single_wallet`
  keeps its `covers_requirement` ID and gains the body-row assertion), managed
  `web/tests/browser/test_browser_inventory_grid.py`
  (add section/description assertions; keep tile/inspector assertions),
  `web/tests/browser/test_browser_contextual_hud.py` bag sections if it pins
  the old structure.
- Spec traceability: modified requirements keep their existing requirement
  headers, so existing `covers_requirement` IDs remain valid; new assertions
  extend the already-annotated tests.
- No player command surface change, so `docs/game/commands.md` is untouched.
- No backward compatibility work (unreleased project, no live users).

## Related changes (not in scope here)

- `remove-redundant-dock-menu-layout`: drops the superfluous
  `.dock-menu-layout` wrapper the mock's `.dock .pane` has no equivalent of.
- `align-drawer-chrome-symbols`: mock-faithful head icon (`背包` backpack
  outline) and the 46px command-line clearance for the drawer top edge.
