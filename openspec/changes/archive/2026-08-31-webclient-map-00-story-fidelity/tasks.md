# Tasks: webclient-map-00-story-fidelity

## 1. Shared derived-shape helper

- [x] 1.1 In `web/webclient-app/stories/fixtures.js`, export `localMapModelFor(fixture)` returning the EXACT store-side shape `{ ...LocalMapModel.reducePanel(fixture), available: fixture.available !== false, reason: fixture.reason }` — byte-identical to `stores/elosern.js`'s `localMapModel` construction (import the same `lib/local_map.js` façade the MapLattice stories use). The helper is the store conversion and nothing else: it never mutates, duplicates, or synthesizes fixture data.
- [x] 1.1b Fix the prop-field bug the derived-shape rebind exposes: `LocalMap.vue` initializes its selection from `props.localMap.current_node` (raw-payload field) while the live store passes the reducer's `currentNode`, so the production detail line mounts blank. Read `currentNode` instead, and migrate `tests/world/local_map.test.js` mounts to helper-built models so they exercise the live shape.
- [x] 1.1c Add a focused Vitest case pinning the helper against the store construction: for one available fixture and for `LOCAL_MAP_UNAVAILABLE_SAMPLE`, `localMapModelFor(fixture)` equals the store's `{ ...reducePanel(p), available: p.available !== false, reason: p.reason }` field-for-field, and the unavailable model preserves the registry-owned reason message (the rebinding must not regress the unavailable branch).

## 2. Rebind the degenerate stories

- [x] 2.1 `stories/World/LocalMap.stories.js`: pass every `localMap` arg through `localMapModelFor` (all six stories: FullLattice, Wilderness, Instance, Interior, Minimal, Unavailable).
- [x] 2.2 `stories/Overlays/MapOverlay.stories.js`: same rebinding for FullLattice, Minimal, Unavailable.
- [x] 2.2b `stories/Overlays/OverlayHost.stories.js`: the `MapSurface` story renders MapOverlay with the raw `LOCAL_MAP_SAMPLE` (arg and slot fallback) — bind both through `localMapModelFor` so every story of the MapOverlay component family uses the shared helper (the delta's family-wide clause).
- [x] 2.2c `stories/World/MapLattice.stories.js`: delete the private `modelFor` copy and import the shared helper (its fixtures are all available-form, so behavior is unchanged).
- [x] 2.3 Verify in the running Storybook that `World/LocalMap — FullLattice` renders the full multi-node lattice (viewBox spans the fixture's `cols/rows`, not `0 0 58 58`) and each node label appears. VERIFIED (dev server): viewBox `0 0 174 58` (3×1 lattice), node ids `grid:altoria:{1,2,0}:2`, visible labels 霧骨渡口 / 南門 / 碼頭.

## 3. Missing-state stories

- [x] 3.1 Add an actionable-node story: island-scale derived model where an adjacent node carries the `move` action descriptor (the existing fixture has one). The actionable halo renders unconditionally for any node with an `action` (there is no focus state for SVG `<g>` nodes), so this is a STATIC story documenting the halo + committed move intent; no play function, no dispatch. The interaction contract stays covered by the existing Vitest mount tests (halo present, click emits the exact intent).
- [x] 3.2 Add a focused-remembered story: play function focuses a remembered-list item (the `li` is `tabindex=0`) and the detail line renders that node's name and explored state with no `→` travel affordance (the detail line carries no landmark field — document exactly what renders). Review follow-up (rubber-duck): the play contract is OBSERVABLE (throws on missing item, lost focus, or wrong detail text) and the interaction is pinned in jsdom by a real `focus()` unit test (not click) in `tests/world/local_map.test.js`. VERIFIED (dev server): `li` focused, detail line `舊街區 · 已探索 · (5, 5)`, no `→`.
- [x] 3.3 Add a tall-lattice story proving the scale-down path: bind `LOCAL_MAP_TALL_LATTICE_SAMPLE` through `localMapModelFor` (its 2×64 lattice is already 116×2830px natural vs the 206/296 caps, so no new fixture is needed). Name the story `TallLatticeScaled`; its doc records the natural size and the proportional scale `min(206/W, 296/H)` (≈12.1×296 — the width cap is a bound, not an attained width). Pair it with a Vitest case asserting only what jsdom can prove (canvas style max-width/max-height wiring), and verify real rendered scaling/overflow in the running Storybook (browser), recording the measurement. VERIFIED (dev server): natural 116×2830; inline caps bind as `max-width: 206px; max-height: 296px`; rendered box 14.1×298 (aspect-preserving scale — 2830→296 gives 116×(296/2830)≈12.1, the rendered 14.1 width carries the SVG border box); the document scroll box stays 1365×768, no overflow. FocusedRemembered VERIFIED: `li` focused, detail line `舊街區 · 已探索 · (5, 5)`, no `→`. ActionableNode VERIFIED: exactly one halo, on `grid:altoria:2:2`.

## 4. Roadmap governance

- [x] 4.1 Append the three map waves as new rows of the delivery table in `docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` §6 (`webclient-map-00-story-fidelity` (depends on H6) → `webclient-map-01-draft-chrome` → `webclient-map-02-layout-variants`), following §9's tracker rule: M0 lands as `In-progress` (it is the change being implemented), M1/M2 as `Planned`; M0 flips to `Done` under §9's completion conditions at archive time. Note in §6 that the map waves amend the table under §9.

## 5. Gates

- [x] 5.1 `npm test` green (story fixture contracts). 68 files / 586 tests passed; the dependency-free Node gate: 377 pass / 0 fail.
- [x] 5.2 `npm run build-storybook` + `npm run showcase-coverage` green (no manifest change; new stories live under listed titles). 41/41 required components covered.
- [x] 5.3 `uv run --locked python -m tools.spec_traceability check` green (amended requirement keeps its heading and owner tests). 1128/1128 covered, 0 errors.
- [x] 5.4 `openspec validate webclient-map-00-story-fidelity --strict` passes. `openspec validate --all --strict`: 181/181. `git diff --check` clean.
