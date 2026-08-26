## 1. Prerequisite check

- [ ] 1.1 Confirm `fix-webclient-local-map-node-crowding` has landed (its corrected pitch/marker-size
      constants are what this change extracts and parameterizes). If it has not yet landed, land it
      first — do not re-derive spacing constants independently here.
- [ ] 1.2 Refresh this change's `specs/webclient-local-map/spec.md` delta to include whatever new
      scenarios the crowding fix's own delta added to the "browser minimap renders states without
      relying on color alone" requirement (it modifies the same requirement this change modifies).
      `openspec archive` replaces a `MODIFIED` requirement's on-disk text wholesale and fails if the
      on-disk requirement carries a scenario this delta's block omits — do not skip this rebase.

## 2. Extract MapLattice.vue

- [ ] 2.1 Create `web/webclient-app/components/MapLattice.vue`, moving `LocalMap.vue`'s SVG lattice
      block (nodes, markers, connector edges, per-node labels) and the state legend into it, along with
      the supporting script logic (`nodePos`, `edgeGeoms`, `edgeClass`, `truncatedLabel`, `legendState`).
      Do **not** move `selectedId`, `hoveredId`, `activeNode`, `detailParts`, or `selectNode` — those
      stay in `LocalMap.vue` because `activeNode` reads from both the lattice's nodes and the
      remembered-node list, and the remembered list's own click handler calls `selectNode` directly.
- [ ] 2.2 Give `MapLattice.vue` `hover(node)`, `leave()`, and `move(payload)` emits in place of owning
      `hoverNode`/`clearHover`/`selectNode`/`activateNode` itself — `activateNode`'s existing "select
      then, if actionable, emit move" logic splits into: the SVG node's `@mouseenter`/`@mouseleave`
      emit `hover`/`leave`; its `@click` emits `move` only when the node carries an exact `move` action
      (no `open-map`-equivalent emit needed here — the "展開全地圖" trigger stays in `LocalMap.vue`,
      never moves into `MapLattice.vue`). Add the scale props (column pitch, row pitch, marker radii,
      label max length) defaulting to the minimap's post-crowding-fix values, plus the existing
      `localMap`/`nodes`/`edges` data props.
- [ ] 2.3 Update `LocalMap.vue` to compose `<MapLattice>` with no scale props passed (defaults apply),
      listening to `@hover`/`@leave` to keep driving its own `selectedId`/`hoveredId`/`activeNode`/
      `detailParts` and its (unmoved) detail-line paragraph, and `@move` forwarded to its existing
      `move` emit. The remembered-node list's `@click="selectNode(node)"` needs no change at all. Keep
      the title/meta row, orientation legend, expand button, and remembered-node list exactly as before.
- [ ] 2.4 Re-run the full existing `webclient-local-map` Vitest/browser coverage against the refactored
      `LocalMap.vue` — same testids, same rendered DOM shape, and specifically confirm clicking/focusing
      a remembered node still updates the shared detail line (no existing test covers this today; add
      one if none exists, since this is exactly the interaction the extraction could silently break).

## 3. Wire MapOverlay.vue to the larger scale

- [ ] 3.1 Update `MapOverlay.vue` to compose `<MapLattice>` directly (not `<LocalMap>`), passing scale
      props sized to fill the overlay body's available width (up to `OverlayHost.vue`'s 900px cap) and
      height, with a longer label-truncation threshold than the minimap's. Wire only `@move` to the
      existing `handleMove`; `@hover`/`@leave` are intentionally left unhandled (no detail line in the
      overlay, per design.md's Non-Goals).
- [ ] 3.2 Confirm the overlay's `unavailable` branch (`MapOverlay.vue:44-51`) is unaffected — it renders
      before the lattice is reached at all.
- [ ] 3.3 Add a browser or Vitest assertion that the overlay's rendered canvas width scales with the
      overlay body's available width (not pinned to the minimap's 206px), and that no marker/label/edge
      collision exists at the overlay's scale (reusing the crowding fix's non-intersection assertion
      pattern, parameterized for the overlay's viewport).
- [ ] 3.4 Confirm `explore.move` submission from a node activated inside the overlay still submits
      exactly one envelope and the overlay's rendered lattice updates from the refreshed payload.

## 4. Stories and manifest

- [ ] 4.1 Add `World/MapLattice` stories at the minimap scale and the overlay scale, reusing existing
      `LOCAL_MAP_SAMPLE`/`LOCAL_MAP_WILDERNESS_SAMPLE`/`LOCAL_MAP_MINIMAL_SAMPLE` fixtures.
- [ ] 4.2 Add `"World/MapLattice"` to `component-manifest.json`'s `required` array; run
      `npm run build-storybook && npm run showcase-coverage` to confirm the manifest and the built
      showcase agree.
- [ ] 4.3 Spot-check `World/LocalMap.stories.js` and `Overlays/MapOverlay.stories.js` still render
      correctly through the new composition (no args changes expected, since the payload contract is
      unchanged).

## 5. Close out

- [ ] 5.1 Re-screenshot the client at 1440×900, open "展開全地圖", and visually confirm the overlay now
      shows a spacious, legible map instead of the minimap's small canvas centered in empty space.
- [ ] 5.2 `openspec validate improve-webclient-map-overlay-scale --strict`; before archiving, re-confirm
      task 1.2's spec-delta rebase against whatever `openspec/specs/webclient-local-map/spec.md` looks
      like after the crowding fix has actually archived (not just at proposal-drafting time).
- [ ] 5.3 Run the focused JS gates (`npm test`, the dependency-free Node gate, Storybook build +
      component-coverage) and the smallest browser class covering `local-map`/`map-overlay`.
