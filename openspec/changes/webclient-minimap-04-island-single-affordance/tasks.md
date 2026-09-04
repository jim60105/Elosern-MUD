# Tasks — Minimap Island: One Affordance, One Readout

> This change builds on `webclient-minimap-03-canvas-scale-and-budget`'s
> baseline (already in the working tree). Nothing here is landed yet: every
> task below is a real edit.

## 1. The island's single full-map affordance

- [x] 1.1 In `web/webclient-app/components/LocalMap.vue`, delete the meta-row
  `button.local-map__expand`, its inline expand-glyph `<svg>`, and the
  `.local-map__expand`, `.local-map__expand-icon`, `.local-map__expand:hover`
  and `.local-map__expand:focus-visible` rules. Proof:
  `web/webclient-app/tests/world/local_map.test.js` — the header assertion
  becomes "the header carries the title and the axis marks and no full-map
  control".
- [x] 1.2 In the same file, render as the FIRST child of the available branch a
  content-free `<button type="button" class="local-map__affordance"
  data-testid="local-map__expand" aria-label="展開全地圖" title="展開全地圖"
  @click="emit('open-map')">`. Proof: `local_map.test.js` — the affordance is a
  `button` element, carries the accessible name 展開全地圖, has no child
  elements, and is the island's first tab stop.
- [x] 1.3 Add the layering CSS (design D1): `position: relative` on
  `.local-map`; `.local-map__affordance { position: absolute; inset: 0;
  z-index: 0; padding: 0; border: 0; background: transparent; cursor: pointer;
  border-radius: var(--radius) }`; and
  `.local-map > *:not(.local-map__affordance) { position: relative; z-index: 1 }`
  so a future island child is raised by construction rather than by opt-in.
  Proof: `local_map.test.js` — the raising rule is a `:not()` rule on the
  island's direct children, and a lattice-node click still moves (task 1.5).
- [x] 1.4 Give the affordance a `:focus-visible` treatment that draws on its own
  (island-sized) box — an outline in the island's focus token with a negative
  offset so it sits inside the card's radius — rather than a corner indicator or
  a `:has()` rule on the root. Proof: `local_map.test.js` asserts the ring is
  declared on the affordance itself; the browser suite (wave 5) is the visual
  gate.
- [x] 1.5 Leave `onIslandClick` and its
  `closest("button, a, [tabindex], [data-node]")` guard untouched, and confirm
  every path emits exactly one `open-map`. Proof: `local_map.test.js` — one
  emit for a body click, one for an affordance click, one for a keyboard
  activation (a `click` on the button), and ZERO for a click on an actionable
  lattice node, its marker, or a remembered entry (which submits its move /
  takes focus instead).
- [x] 1.6 Confirm the island root still carries no `role` and no `tabindex`, and
  that `role="button"` appears nowhere on it. Proof: the existing
  `local_map.test.js` assertion "keeps the island root non-interactive (no role,
  no tabindex)" stays green unchanged.

## 2. The island's readout

- [x] 2.1 In `LocalMap.vue`, remove `selectedId`, `hoveredId`, `activeNode`,
  `STATE_LABELS`, `selectNode`, `hoverNode`, `clearHover`, the
  `watch(() => props.localMap.currentNode)` re-seed, and the
  `@select`/`@hover`/`@leave` bindings on `<MapLattice>`. Leave
  `MapLattice.vue`'s emits in place (the shared renderer keeps its event
  surface). Proof: `local_map.test.js` — hovering and activating a node leave
  the readout unchanged; `tests/world/map_lattice.test.js` and
  `tests/overlays/map_overlay.test.js` stay green with no renderer edit.
- [x] 2.2 Replace `detailParts` with a single computed that yields
  `座標 <x>,<y>` from the payload's current node when `layer` is `grid` or
  `wilderness`, and the empty string otherwise; keep the element mounted with
  its `local-map-detail` testid and the `--empty` modifier change 03
  introduced. Proof: `local_map.test.js` — a wilderness payload at (60, 107)
  reads exactly the coordinate figure with no place name, no 目前所在, and no
  destination; an interior payload's line is empty and hidden.
- [x] 2.3 Restyle `.local-map__detail` to the token-driven readout treatment
  (design D7): the island's smallest type step, `var(--f-mono)`, centred,
  `var(--paper-500)`, spaced from the canvas with a `--sp-*` step, no border,
  no background, no padding. Proof: `local_map.test.js` — no border/background
  declaration remains on the rule and no draft hex literal is introduced.
- [x] 2.4 Confirm the remembered list's own item label is untouched, so a
  focused remembered node still shows its name without the readout. Proof: the
  existing "Focused remembered node offers no travel action" coverage in
  `local_map.test.js` stays green.

## 3. The top-meta location

- [x] 3.1 In `web/webclient-app/stores/elosern.js`, replace
  `statusSlice.locationLabel`'s single expression with the fixed fallback order
  (design D5): the committed `local_map` panel's current node label → the status
  panel's `actor.location.label` → null. Keep the derivation in the store; do
  not touch `TopBar.vue` or `AppShell.vue`. Proof:
  `web/webclient-app/tests/store/store_slices.test.js` — a wilderness snapshot
  whose status label is `Wilderness` and whose map current node is
  西部丘陵與谷地 yields 西部丘陵與谷地.
- [x] 3.2 Cover every fallback branch in the same suite: map panel absent; map
  panel `available: false`; `current_node` naming a node the panel's `nodes` do
  not carry; a node whose `label` is an empty string; both panels absent
  (`locationLabel === null`, so `TopBar` renders 「位置：--」). Proof:
  `store_slices.test.js` plus the unchanged `tests/top_bar.test.js`.

## 4. Stories

- [x] 4.1 Update `web/webclient-app/stories/World/LocalMap.stories.js` so the
  island stories show the single-affordance island and the coordinate-only
  readout (and a coordinate-free story whose readout is absent). Proof:
  `npm run build-storybook && npm run showcase-coverage` green — no new
  components, manifest unchanged.

## 5. Browser contract

- [x] 5.1 Re-run `web/tests/browser/test_browser_contextual_hud.py`'s overlay
  trigger test unchanged: `[data-testid="local-map__expand"]` still clicks open
  the map overlay and Escape still restores focus to that element — the moved
  testid (design D4) is what keeps this gate meaningful.
- [x] 5.2 Extend `test_browser_contextual_hud.py` under
  `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`:
  the island renders exactly one full-map affordance and no labelled/icon
  control; keyboard Enter on the focused affordance opens the overlay; a click
  on an actionable lattice node moves without opening the overlay.
- [x] 5.3 Extend `web/tests/browser/test_browser_shell.py`'s
  `test_header_shows_location_time_and_connection_dot` (already anchored on
  `webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable`):
  on a wilderness snapshot the top-meta location shows the region name and is
  not the raw room key `Wilderness`.
- [x] 5.4 Re-run `test_browser_local_map.py`, `test_browser_layout.py` and
  `test_browser_shell.py` unchanged as the island-bounds regression gate: the
  island must still fit its anchor without the `overflow-y` fallback with the
  header 24px shorter and the readout one line.
- [x] 5.5 Confirm `node --test web/static/webclient/js/tests/*.test.js` is
  untouched and green — this change makes no edit to the preserved UMD render
  model or its dependency-free Node gate.

## 6. Verification

- [x] 6.1 `npm test` (Vitest) green.
- [x] 6.2 `npm run build-storybook && npm run showcase-coverage` green.
- [x] 6.3 Browser classes in wave 5 green locally within the one-class budget,
  or deferred to CI per repo policy where they exceed it.
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check` green — all
  three requirements are MODIFIED in place with no rename, so every existing
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`,
  `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`
  and `webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable`
  anchor stays valid.
- [x] 6.5 `openspec validate webclient-minimap-04-island-single-affordance
  --strict` green.
