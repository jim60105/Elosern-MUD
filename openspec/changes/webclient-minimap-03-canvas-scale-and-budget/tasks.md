# Tasks — Minimap Canvas Scale and Height Budget

> The working tree already carries a green baseline for waves 1–4 (the pass
> described in the proposal). Those tasks are therefore "confirm the landed edit
> matches the requirement as written and reviewed", not "write from scratch" —
> if review changes a decision, the corresponding task becomes a real edit.

## 1. Shared renderer: one width bound

- [ ] 1.1 In `web/webclient-app/components/MapLattice.vue`, add
  `maxUpscale: { type: Number, default: null }` (`null` = uncapped) and document
  that the default keeps `MapOverlay.vue` filling its own body width untouched.
  Proof: `web/webclient-app/tests/world/overlays/map_overlay.test.js` and
  `world/map_lattice.test.js` stay green with no overlay edit.
- [ ] 1.2 In the same file, add `widthCaps()` folding `maxWidth`,
  `maxHeight × canvasWidth / canvasHeight`, and `canvasWidth × maxUpscale` into
  one list, and emit `max-width: floor(min(caps) × 100) / 100 px` from
  `latticeStyle` (keeping `max-height` as the belt-and-braces cap). Proof:
  `web/webclient-app/tests/world/local_map.test.js` — the 116 × 2830 canvas under
  a 296px budget asserts `max-width: 12.13px` alongside `max-height: 296px`.
- [ ] 1.3 Update `.local-map__lattice`'s CSS and comments so `align-self: center`
  is documented as centring a capped canvas rather than defending a natural-size
  render. Proof: the upscale-bound assertion in 3.2 (a 116px canvas centred in a
  210px content box).

## 2. Island height budget: a fixed point

- [ ] 2.1 In `web/webclient-app/components/LocalMap.vue`, add
  `ANCHOR_BOTTOM_CLEARANCE = 12` and `anchorHeightBudget(anchor)` measuring
  `floor(dockTop − anchorTop − 12)` from `getBoundingClientRect()`, with the
  bare-mount fallback to `anchor.clientHeight` for component/Storybook mounts
  that have no dock sibling. Proof: `local_map.test.js` — "budgets against the
  anchor's room, not the island's own height".
- [ ] 2.2 Make `measureCanvasBudget()` read that budget instead of
  `anchor.clientHeight`, leaving the section/gap/fixed-chrome arithmetic and the
  `[40, 296]` clamp unchanged, and document the collapse
  (`available = renderedCanvasHeight − 1`) the old read produced. Proof: the same
  test drives 8 measurement passes against a hostile anchor whose `clientHeight`
  reports the island's own rendered height and requires an identical cap on every
  pass.

## 3. Island: fill the card, survive any title, say nothing when empty

- [ ] 3.1 In `LocalMap.vue`, pass `:fill-width="true" :max-upscale="2"` to
  `<MapLattice>` and add `width: 100%` to `.local-map` so the card claims the
  anchor's 230px column instead of being shrink-to-fit under
  `align-items: flex-end`. Proof: `local_map.test.js` — "fills the island's width
  instead of drawing at natural pixel size" (`width: 100%` + `max-width: 206px`).
- [ ] 3.2 Confirm the upscale bound on a one-node payload: natural 58 × 58 caps at
  116px. Proof: `local_map.test.js` — "bounds the upscale so a one-room payload
  cannot blow up the marker ramp".
- [ ] 3.3 Re-budget `.local-map__meta`: drop `justify-content: space-between` for
  `gap: var(--sp-2)`; make `.local-map__meta-title` the only elastic item
  (`flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis`) and bind `:title="title"` on it; make
  `.local-map__orientation` and the trailing control `flex: none`. Proof:
  `local_map.test.js` — "keeps the header on one row: an elastic title, fixed
  marks, a fixed trigger".
- [ ] 3.4 Add the `watch(() => props.localMap.currentNode)` that re-seeds
  `selectedId` and clears `hoveredId`, plus the `activeNode` fallback to the
  payload's current node via `nodeWithId()`. Proof: `local_map.test.js` —
  "re-seeds the readout when the payload's current node moves" and "falls back to
  the current node when a targeted update drops the selection".
- [ ] 3.5 Drop the detail line's border/padding for the draft's unboxed
  `.compass`-style readout and add the `local-map__detail--empty` modifier
  (`display: none`) applied when `detailParts.length === 0`, keeping the element
  mounted for the `local-map-detail` testid and the body-click target. Proof:
  `local_map.test.js` — "states nothing rather than an empty box when no node
  resolves" (and `sectionHeight` reads 0 for the hidden section).

## 4. Stories

- [ ] 4.1 In `web/webclient-app/stories/World/MapLattice.stories.js`, render
  island-scale stories in a 210px content box (the 230px column less the island's
  padding and border) and pass `fillWidth: true, maxUpscale: 2` so a story shows
  the canvas the island actually draws. Proof: `npm run build-storybook &&
  npm run showcase-coverage` green (no new components, manifest unchanged).

## 5. Regression gates for the island's bounds

- [ ] 5.1 Re-run `web/tests/browser/test_browser_local_map.py` unchanged: the
  island's viewport-bounds and no-overprint scenarios must stay green with the
  canvas now filling the card, at 1440×900 and 1280×720.
- [ ] 5.2 Re-run `web/tests/browser/test_browser_contextual_hud.py`,
  `test_browser_layout.py`, and `test_browser_shell.py` unchanged: the island must
  still fit its anchor without the `overflow-y` fallback, and must not intersect
  the dock, the caption, or the opposite anchor.
- [ ] 5.3 Confirm `node --test web/static/webclient/js/tests/*.test.js` is
  untouched and green — this change makes no edit to the preserved UMD render
  model or its dependency-free Node gate.

## 6. Verification

- [ ] 6.1 `npm test` (Vitest) green.
- [ ] 6.2 `npm run build-storybook && npm run showcase-coverage` green.
- [ ] 6.3 Browser classes in wave 5 green locally within the one-class budget, or
  deferred to CI per repo policy where they exceed it.
- [ ] 6.4 `uv run --locked python -m tools.spec_traceability check` green — the
  requirement is MODIFIED in place with no rename, so every existing
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  anchor stays valid.
- [ ] 6.5 `openspec validate webclient-minimap-03-canvas-scale-and-budget
  --strict` green.
