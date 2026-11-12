# Design: gallery wall with inline image tray

## Context

- `components/handbook/TileWall.vue` is the shared roving listbox: one
  `role="listbox"`, one `tabindex=0` item (focused, else selected, else
  first), ArrowLeft/Right ±1, ArrowUp/Down ± measured columns
  (`getComputedStyle(grid).gridTemplateColumns`), Home/End, Enter/Space/click
  select. It renders square tiles in one grid per group.
- The prototype `docs/design/gallery-window/GalleryWall.vue` shows the tile
  shapes, tray wash/notch and tile marks with synthetic data (reference only;
  never imported).
- `ArtworkPreview.vue` renders a committed artwork descriptor
  (`:artwork`, `:panel`, `:view-subject-id`, `:alt`).
- Tokens: sizes `calc(<n>px * var(--ui-scale))`, text `--text-*` (never below
  `--text-xs`), durations `--motion-*`;
  `tests/components/window_primitives_styles.test.js` shows the style-lint
  pattern to copy.

## Goals / Non-Goals

**Goals:** a self-contained, unmounted wall component with stories and tests.

**Non-Goals:** the image page, editors, dispatch, rail (later changes);
collapsible people group headings (`gallery-people-client`).

## Decisions

### D1. Component contract (verbatim)

```js
// GalleryWall.vue
props: {
  groups:          { type: Array, required: true },   // committed v4 groups
  selectedSubject: { type: String, default: null },   // committed `selected`
  cards:           { type: Array, default: () => [] },// committed cards of selected
  officialEntries: { type: Array, default: () => [] },
  capabilities:    { type: Object, default: null },   // committed capabilities
  selectedImage:   { type: String, default: null },   // image_id | official identity | "generate"
  panel:           { type: Object, default: null },   // for ArtworkPreview
  ariaLabel:       { type: String, required: true },  // category label
  pendingSubject:  { type: String, default: null },   // in-flight select → aria-busy
}
emits: ["select-subject", "select-image", "generate", "focus-lost"]
expose: { focusOwner(), focusFirst() }
```

`select-image` carries a card `image_id` or an official `identity`;
`generate` is emitted by the 生成新圖 tile.

### D2. Model helpers (`components/gallery-window-model.js`, pure)

```js
export const GENERATE_TILE = "generate";
export function tileShape(kind)          // "landscape" for "scene", else "portrait"
export function trayOpen(capabilities)   // capabilities !== null && capabilities.max_cards !== 1
export function wallTiles(groups)        // [{ groupKey, subject }] in reading order, expanded groups only
export function trayItems(cards, officialEntries)
  // [{ id, kind: "card"|"generate"|"official", row }] — cards in payload order,
  // then { id: GENERATE_TILE, kind: "generate" }, then officials
export function trayInsertIndex(ownerIndex, columns, groupLength)
  // min(groupLength - 1, ceil((ownerIndex + 1) / columns) * columns - 1)
```

### D3. Layout and tray placement

- Each group is a `<section role="group">` (heading `<h3>` only when `label`
  is non-null, plus `<span>seen / total</span>` when both present) with one
  CSS grid; portrait tiles `aspect-ratio: 9 / 16`, landscape `16 / 9`.
- Columns are read with a `ResizeObserver` on the selected subject's group
  grid (`gridTemplateColumns` token count); the tray is rendered inside that
  grid after the tile at `trayInsertIndex(...)` with `grid-column: 1 / -1`.
- Tray chrome: seal-coloured wash, border and a notch under the owner tile
  (`--tray-notch-x` set from the owner's offset). Opening calls
  `trayEl.scrollIntoView({ block: "nearest", behavior })` with `behavior`
  `"auto"` when `matchMedia("(prefers-reduced-motion: reduce)")` matches or
  the root motion level is `off`, else `"smooth"`.
- The wall scroller has `scrollbar-gutter: stable`.

### D4. Keyboard and focus

- Wall: copy TileWall's roving logic over `wallTiles(groups)`; tray tiles are
  not part of the wall's item list.
- Tray: its own `role="listbox"` with `aria-label="<display_name>的圖片"`,
  one `tabindex=0` item (selected image, else first), ArrowLeft/Right/Home/End
  in order, Enter/Space/click emit `select-image` or `generate`; Escape calls
  `event.stopPropagation()`, `preventDefault()` and focuses the owner tile.
- Owner tile: `aria-expanded` only when `trayOpen(capabilities)`.
- After each `groups` change, if the previously focused tile's subject key is
  absent and focus was inside the wall, emit `focus-lost` once.
- Tile accessible name: display name, plus 操作中 when current, plus
  `（N 張）` when `card_count > 1`.

### D5. Tests and stories

- `tests/components/gallery_wall.test.js` (Vitest + @vue/test-utils): one test
  per ADDED scenario; `trayInsertIndex` unit cases; a style lint like
  `window_primitives_styles.test.js` for this component.
- `stories/Data/GalleryWall.stories.js`: Mine (tray open on the live
  character), Party, Monster (tier groups, no tray), Empty, TrayStates
  (default/pending/failed/official), each at `atReference` and one at
  `atFullHd`; fixtures in `stories/gallery-fixtures.js` built in the v4
  shape. Add `"Data/GalleryWall"` to `component-manifest.json` `required`.
- Fixture validity: a Node test validates every story fixture with the v4
  validator exported by `gallery-v4-validators` (`validateGalleryPanelV4`
  before the cutover, `validateGalleryPanel` after it).

## Review

Visual fidelity to the approved prototype (tile proportions, tray wash and
notch, ribbon placement) is human-reviewed in Storybook at 1451×790 and
1920×1080; it is not asserted by tests.

## Risks / Trade-offs

- [Measured columns lag a resize by one frame] → the tray re-places on the
  observer callback; no layout assertion depends on timing.
