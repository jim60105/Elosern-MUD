## 1. Reproduce and pin down the defect

- [x] 1.1 Add a Storybook story (or reuse `LOCAL_MAP_SAMPLE`) rendered at the island's real `230px`
      width and capture the current overlap visually, as a before-state reference for the fix.
- [x] 1.2 Extend the existing `web/tests/browser/test_browser_local_map.py::
      test_minimap_content_stays_inside_its_island` overlap check (do not add a redundant parallel
      check): its current no-overlap comparison tolerates a `+1`px boundary (`boxes[i]["right"] <=
      boxes[j]["left"] + 1`, etc.), which accepts exactly-touching (0px gap) or ~1px-overlapping boxes as
      passing — this is why the reported zero-gap crowding shipped without failing this test. Tighten
      the comparison to require a small strictly-positive minimum visible gap (e.g. `>= 2px` between any
      two marker bounding boxes) and add the same non-intersection check for the `local-map__node-label`
      elements (marker-vs-marker, marker-vs-label, and label-vs-label), not just marker-vs-marker. Get
      this red against today's code before starting task 2.

## 2. Fix the lattice geometry in LocalMap.vue

- [x] 2.1 Replace the single `CELL` constant with separate column-pitch and row-pitch constants sized so
      a node's marker + its label's rendered line height + a minimum gap fit before the next row.
- [x] 2.2 Update `nodePos` to use the column pitch for `x` and the row pitch for `y`, and update
      `canvasWidth`/`canvasHeight` accordingly (keep `LABEL_BAND` as the trailing margin below the last
      row).
- [x] 2.3 Re-tune marker radii (`local-map__marker--*`) and/or `LABEL_MAX` only if the new pitch alone
      does not clear horizontal label-to-label crowding on a full row of adjacent nodes.
- [x] 2.4 Verify the connector `<line>` elements are no longer fully occluded by the (now correctly
      spaced) markers at the new pitch.

## 3. Verify no regression to existing behavior

- [x] 3.1 Confirm `activateNode`/`explore.move` submission still targets the correct node after the
      marker/cell size change (task 2 must not touch `edgeGeoms`, `nodeById`, or `activateNode`).
- [x] 3.2 Re-run the existing `webclient-local-map` browser/Vitest coverage plus the new assertion from
      task 1.2 until green.
- [x] 3.3 Re-check the H2 island-vs-dock non-overlap browser assertion at 1440×900 and 1280×720 (roadmap
      §8 risk item) now that the island's natural height may grow on multi-row rooms.
- [x] 3.4 Visually re-verify `MapOverlay.vue` ("展開全地圖") inherits the fix with no code change of its
      own, using the same room/payload used for the before-state capture in task 1.1.
- [x] 3.5 Add a maximal-height, minimal-width lattice fixture (e.g. a narrow 2-column × 64-row payload,
      within the model's legal 64×64 bound) and confirm the island's `overflow-y: auto` fallback
      (`LocalMap.vue`'s `.local-map` rule) still degrades acceptably rather than assuming today's
      typical multi-row/multi-column fixtures exercise this worst case — the new row pitch increases
      this lattice's natural height by roughly the same ratio as the pitch increase, so it is materially
      worse than before the fix even though it is a pre-existing, not newly introduced, edge.

## 4. Close out

- [x] 4.1 `openspec validate fix-webclient-local-map-node-crowding --strict`.
- [x] 4.2 Run the focused JS gates (`npm test`, the dependency-free Node gate) and the smallest browser
      class covering `local-map`.
