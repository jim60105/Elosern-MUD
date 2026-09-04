# Tasks — Minimap Canvas Scale and Height Budget

> The working tree already carries a green baseline for waves 1–4 (the pass
> described in the proposal). Those tasks are therefore "confirm the landed edit
> matches the requirement as written and reviewed", not "write from scratch" —
> if review changes a decision, the corresponding task becomes a real edit.

## 1. Shared renderer: one width bound

- [x] 1.1 In `web/webclient-app/components/MapLattice.vue`, add
  `maxUpscale: { type: Number, default: null }` (`null` = uncapped) and document
  that the default keeps `MapOverlay.vue` filling its own body width untouched.
  Proof: `web/webclient-app/tests/world/overlays/map_overlay.test.js` and
  `world/map_lattice.test.js` stay green with no overlay edit.
  **Verified 2026-09-04**: landed as-specified at `MapLattice.vue:49`;
  `MapOverlay.vue` has zero diff against the pre-`f69d164` tree (`git diff
  <parent-of-f69d164>..HEAD -- web/webclient-app/components/MapOverlay.vue`
  is empty).
- [x] 1.2 In the same file, add `widthCaps()` folding `maxWidth`,
  `maxHeight × canvasWidth / canvasHeight`, and `canvasWidth × maxUpscale` into
  one list, and emit `max-width: floor(min(caps) × 100) / 100 px` from
  `latticeStyle` (keeping `max-height` as the belt-and-braces cap). Proof:
  `web/webclient-app/tests/world/local_map.test.js` — the 116 × 2830 canvas under
  a 296px budget asserts `max-width: 12.13px` alongside `max-height: 296px`.
  **Verified 2026-09-04**: `widthCaps()` and `latticeStyle` at
  `MapLattice.vue:339-358` match verbatim; the named assertion is present in
  `local_map.test.js` and passes under `npm test` (see §6.1).
- [x] 1.3 Update `.local-map__lattice`'s CSS and comments so `align-self: center`
  is documented as centring a capped canvas rather than defending a natural-size
  render. Proof: the upscale-bound assertion in 3.2 (a 116px canvas centred in a
  210px content box).
  **Verified 2026-09-04**: comment block at `MapLattice.vue:552-570` states
  exactly this.

## 2. Island height budget: a fixed point

- [x] 2.1 In `web/webclient-app/components/LocalMap.vue`, add
  `ANCHOR_BOTTOM_CLEARANCE = 12` and `anchorHeightBudget(anchor)` measuring
  `floor(dockTop − anchorTop − 12)` from `getBoundingClientRect()`, with the
  bare-mount fallback to `anchor.clientHeight` for component/Storybook mounts
  that have no dock sibling. Proof: `local_map.test.js` — "budgets against the
  anchor's room, not the island's own height".
  **Verified 2026-09-04**: `ANCHOR_BOTTOM_CLEARANCE` and `anchorHeightBudget()`
  at `LocalMap.vue:159-187` match verbatim, including the worked example in
  design.md D1 (anchor top 64, dock top 500 ⇒ budget 424).
- [x] 2.2 Make `measureCanvasBudget()` read that budget instead of
  `anchor.clientHeight`, leaving the section/gap/fixed-chrome arithmetic and the
  `[40, 296]` clamp unchanged, and document the collapse
  (`available = renderedCanvasHeight − 1`) the old read produced. Proof: the same
  test drives 8 measurement passes against a hostile anchor whose `clientHeight`
  reports the island's own rendered height and requires an identical cap on every
  pass.
  **Verified 2026-09-04**: `measureCanvasBudget()` at `LocalMap.vue:189-215`
  reads `anchorHeightBudget(anchor)`, keeps the `[40, 296]` clamp
  (`Math.max(40, Math.min(296, available))`), and the ratchet-regression test
  ("budgets against the anchor's room, not the island's own height") is present
  and green.

## 3. Island: fill the card, survive any title, say nothing when empty

- [x] 3.1 In `LocalMap.vue`, pass `:fill-width="true" :max-upscale="2"` to
  `<MapLattice>` and add `width: 100%` to `.local-map` so the card claims the
  anchor's 230px column instead of being shrink-to-fit under
  `align-items: flex-end`. Proof: `local_map.test.js` — "fills the island's width
  instead of drawing at natural pixel size" (`width: 100%` + `max-width: 206px`).
  **Verified 2026-09-04**: `LocalMap.vue:322-323` and `:403`.
- [x] 3.2 Confirm the upscale bound on a one-node payload: natural 58 × 58 caps at
  116px. Proof: `local_map.test.js` — "bounds the upscale so a one-room payload
  cannot blow up the marker ramp".
  **Verified 2026-09-04**: named test present and green.
- [x] 3.3 Re-budget `.local-map__meta`: drop `justify-content: space-between` for
  `gap: var(--sp-2)`; make `.local-map__meta-title` the only elastic item
  (`flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis`) and bind `:title="title"` on it; make
  `.local-map__orientation` and the trailing control `flex: none`. Proof:
  `local_map.test.js` — "keeps the header on one row: an elastic title, fixed
  marks, a fixed trigger".
  **Verified 2026-09-04**: `LocalMap.vue:426-508` matches verbatim (no
  `justify-content: space-between` remains anywhere in the file).
- [x] 3.4 Add the `watch(() => props.localMap.currentNode)` that re-seeds
  `selectedId` and clears `hoveredId`, plus the `activeNode` fallback to the
  payload's current node via `nodeWithId()`. Proof: `local_map.test.js` —
  "re-seeds the readout when the payload's current node moves" and "falls back to
  the current node when a targeted update drops the selection".
  **Verified 2026-09-04**: `LocalMap.vue:84-99`.
- [x] 3.5 Drop the detail line's border/padding for the draft's unboxed
  `.compass`-style readout and add the `local-map__detail--empty` modifier
  (`display: none`) applied when `detailParts.length === 0`, keeping the element
  mounted for the `local-map-detail` testid and the body-click target. Proof:
  `local_map.test.js` — "states nothing rather than an empty box when no node
  resolves" (and `sectionHeight` reads 0 for the hidden section).
  **Verified 2026-09-04**: `LocalMap.vue:368-375` (template) and `:529-546`
  (CSS) — `.local-map__detail` carries no border/padding, and
  `.local-map__detail--empty { display: none; }` is present.

## 4. Stories

- [x] 4.1 In `web/webclient-app/stories/World/MapLattice.stories.js`, render
  island-scale stories in a 210px content box (the 230px column less the island's
  padding and border) and pass `fillWidth: true, maxUpscale: 2` so a story shows
  the canvas the island actually draws. Proof: `npm run build-storybook &&
  npm run showcase-coverage` green (no new components, manifest unchanged).
  **Verified 2026-09-04**: story wiring matches (`210px` box, `fillWidth: true,
  maxUpscale: 2`); gate output recorded in §6.2.

## 5. Regression gates for the island's bounds

- [x] 5.1 Re-run `web/tests/browser/test_browser_local_map.py` unchanged: the
  island's viewport-bounds and no-overprint scenarios must stay green with the
  canvas now filling the card, at 1440×900 and 1280×720.
  **Run 2026-09-04**: `uv run --locked python -m unittest
  web.tests.browser.test_browser_local_map -v` (dist rebuilt first via
  `npm run build`) — **13 tests, OK, 94.845s** (both `LocalMapBrowserTest` and
  `LayoutVariantsBrowserTest`). `test_minimap_content_stays_inside_its_island`
  and `test_tall_lattice_with_long_remembered_list_stays_within_the_island`
  each subtest both 1440×900 and 1280×720. No source edit; git diff against
  the pre-run tree is empty.
- [x] 5.2 Re-run `web/tests/browser/test_browser_contextual_hud.py`,
  `test_browser_layout.py`, and `test_browser_shell.py` unchanged: the island must
  still fit its anchor without the `overflow-y` fallback, and must not intersect
  the dock, the caption, or the opposite anchor.
  **Deferred to CI 2026-09-04**: AGENTS.md's browser-test policy caps local
  runs at "one class or file within the budget"; §5.1 already spent that
  budget on `test_browser_local_map.py`, the file most directly exercising
  this change's canvas-fill/height-budget behaviour. These three files are
  unchanged by this commit (no diff touches contextual-HUD, layout, or shell
  code/tests) and are left to the CI browser-shard jobs
  (`.github/browser-shards.json`), consistent with "Local browser testing uses
  one class or file within the budget" / "The full managed browser suite ...
  [is] CI-only."
- [x] 5.3 Confirm `node --test web/static/webclient/js/tests/*.test.js` is
  untouched and green — this change makes no edit to the preserved UMD render
  model or its dependency-free Node gate.
  **Run 2026-09-04**: `node --test web/static/webclient/js/tests/*.test.js` —
  **416 pass, 0 fail**. `web/static/webclient/js/elosern/local_map.js` has zero
  diff against the pre-`f69d164` tree.

## 6. Verification

- [x] 6.1 `npm test` (Vitest) green.
  **Run 2026-09-04**: **76 files, 745 tests, all passed** (4.47s).
- [x] 6.2 `npm run build-storybook && npm run showcase-coverage` green.
  **Run 2026-09-04**: Storybook build completed successfully
  (`.storybook-out/`); showcase-coverage: **"all 42 required component(s)
  have stories and every one of the 42 registered story title(s) is listed
  (42 story title(s) total)"** — frozen manifest, no new components.
- [x] 6.3 Browser classes in wave 5 green locally within the one-class budget, or
  deferred to CI per repo policy where they exceed it.
  **Done 2026-09-04**: `test_browser_local_map.py` run locally (§5.1, 13
  tests OK in 94.845s — well inside the 10-minute local cap in AGENTS.md).
  `test_browser_contextual_hud.py`, `test_browser_layout.py`, and
  `test_browser_shell.py` deferred to CI per §5.2 — this repo's local-browser
  policy is one class/file per run, and none of those three files' subject
  matter (contextual HUD, general layout, shell chrome) is touched by this
  change's diff (which is presently empty against the `f69d164` baseline;
  see §6 verdict below).
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check` green — the
  requirement is MODIFIED in place with no rename, so every existing
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  anchor stays valid.
  **Run 2026-09-04**: **1230 requirements, 4308 associations, 1230 covered, 0
  uncovered, 0 errors.**
- [x] 6.5 `openspec validate webclient-minimap-03-canvas-scale-and-budget
  --strict` green.
  **Run 2026-09-04**: `openspec validate webclient-minimap-03-canvas-scale-and-budget
  --type change --strict` → `Change 'webclient-minimap-03-canvas-scale-and-budget'
  is valid`.

### Verdict

Every wave 1–4 task was confirmed against the landed code at commit
`f69d164` (an ancestor of this branch's base, `master` @ `6a82c48`) with no
divergence from `proposal.md`/`design.md`/`specs/webclient-local-map/spec.md`:
no task required a real code edit. All gates above are green with the counts
recorded inline; `git status`/`git diff` against the branch point show no
component, test, or story source changes — only this `tasks.md` file (and,
if any, `.openspec.yaml`/spec bookkeeping) differ from `master`.
