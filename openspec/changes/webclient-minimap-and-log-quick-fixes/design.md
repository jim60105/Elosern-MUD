## Context

See proposal.md (Why). Current state, verified in code:

- `LocalMap.vue` mounts `MapLattice` with `:max-height="canvasMaxHeight || 296"`, `:fill-width="true"`, `:field-fill="true"`, `:col-pitch="40"`, `:row-pitch="40"`, `:label-font="9"`, `:marker-name-font="10"`, `:show-axis`, `:fog-vignette`, `:show-legend="false"`, `:marker-names`.
  - `canvasMaxHeight` comes from `measureCanvasBudget()`. That function reads `anchorHeightBudget()` (the dock-anchor top minus the hud-right top minus `ANCHOR_BOTTOM_CLEARANCE`), subtracts `sectionHeight()` of the meta row, the remembered list, and the readout, and is re-run by a ResizeObserver on the anchor and by `onUpdated`.
  - The island card is `width: 100%` of the hud-right anchor, which is `calc(var(--right-column) - 28px)` with `--right-column: clamp(230px, 22vw, 360px)`, so it is 332px wide at 1920. It has `padding: 9px` and `border: var(--line)` (1px).
  - `.local-map__lattice` in `map-lattice.css` paints a second `border: var(--line)` plus a background.
- `use-map-lattice-geometry.js` (`layoutGeometry`): with `fieldFill` it pads the field width to `maxWidth` (206) at scale 1. It takes vertical margin `mY = min(mX, verticalSlack)`, so a 3×3 wilderness core of 120 × 134 units sits in a 206-wide canvas and fills about 58% of the width.
  - The graph branch ignores `fieldFill`. The radial canvas is `2 × (maxRadius + LABEL_BOTTOM 26 + PAD 24)` (`RADIAL_GEOMETRY`, exported by `web/static/webclient/js/elosern/local_map.js`), and `width: 100%` scales it to the card: a current-only interior (side 100) is magnified about 2×, and a one-ring interior (side 244) is shrunk.
  - `latticeStyle` resolves `maxWidth` and `maxHeight` into one floored width bound.
- On the graph variant the island renders every `remembered` node as a chip in `ul.local-map__remembered` (`local-map-remembered`). The full-map overlay (`MapOverlay.vue`) renders no remembered list. On the lattice variant, remembered nodes outside the in-view extent are named edge markers, and the visually-hidden mirror `local-map-edge-markers-mirror` states each name with its octant.
- `FullLogOverlay.vue` renders every line into a `position: fixed; overflow-y: auto` dialog and focuses it in `focusSelf()` through `createFocusTrap(...).enter()`. It never sets `scrollTop`, so the log opens at the top.

## Goals / Non-Goals

**Goals:**
- Give the island a constant size whatever the payload holds, and make its drawing fill that size without making any marker or label larger than declared.
- Keep every remembered node readable: to assistive technology on the island, and visibly on the full-map surface.
- Delete the height-budget code path and the requirement text that exists only for it.
- Open the full log at the latest line.

**Non-Goals:**
- The overlay's own geometry (column pitch 280, row pitch 212, `markerScale` 2.2, `maxWidth` 848, `maxHeight` null, `overlayChrome`), its legend, fit, zoom, and pan (C2).
- The hud-right anchor itself and where the island sits in the shell (C4). `ParticipantFrame` and `TitleBallotMenu` stay in the same anchor and keep the anchor's `overflow-y: auto` fallback.
- The render model (`local_map.js`: `edgeMarkersFor`, `layoutRadial`, `RADIAL_GEOMETRY`), the payload, and the presenter.
- Remembered lattice nodes that fall inside the in-view extent. They are not marked today, and that stays as it is.

## Decisions

### D1. A fixed 208px square canvas replaces the measured height budget
`MapLattice` gains `canvasSize` (Number or `null`, default `null`) and loses `fieldFill`. A surface that passes `canvasSize` gets:
- SVG `width` and `height` attributes of `canvasSize`
- a square viewBox of side `S = max(canvasSize, required drawing side)`
- an inline style of `width` and `height` equal to `canvasSize` px, with no width-bound resolution.

The drawn uniform scale is therefore `canvasSize / S ≤ 1` by construction. The island passes `:canvas-size="208"` and no longer passes `max-height`, `fill-width`, or `field-fill`. The overlay passes none of them and keeps its existing path: the `maxWidth` / `maxHeight` single-width-bound rule stays for surfaces without `canvasSize`.

With a constant canvas, the island's height depends only on its fixed rows. `measureCanvasBudget`, `anchorHeightBudget`, `ANCHOR_BOTTOM_CLEARANCE`, `sectionHeight`, `canvasMaxHeight`, the `metaEl` / `rememberedEl` / `detailEl` refs, the ResizeObserver, and `onUpdated` are all deleted.

*Alternative:* keep measuring and cap a square at the budget. Rejected. The requester asked for a fixed station (design §5.1 draws "minimap 208px"), and the measurement was the source of the ratchet bug and of about 60 lines of fixed-point reasoning in the spec.

*Why 208:* the design reference geometry uses it. With 4px padding and 1px border the card is 218px wide, which fits the narrowest supported hud-right anchor (`22vw − 28px` = 253px at 1280 wide).

### D2. Island chrome: one 1px frame, 4px padding, a card of constant size
- `.local-map` changes as follows:
  - `padding: var(--sp-1)` replaces `9px`.
  - It keeps its one `border: var(--line)` (1px), the panel fill, blur, radius, and shadow, so the hud island chrome requirement still holds.
  - `width: auto` replaces `width: 100%`, with `align-self: flex-end`, so the card no longer stretches to the column. The `app-shell.css` override `.elosern-root .local-map { max-width: none; … }` keeps only its border colours.
- `.local-map :deep(.local-map__lattice)` removes the canvas's own border on the island (`border: 0`) and keeps its `--ink-860` ground. The overlay's `--canvas` frame is untouched.
- The readout row always reserves its single line. `.local-map__detail--empty` switches from `display: none` to `visibility: hidden`, so on the graph variant the row states nothing and paints nothing but the card height does not change.

*Alternative:* collapse the empty row. Rejected, because the card would then be two sizes and C4's objective line under the map would move with the layer.

### D3. Lattice fill: pitch-fit first, then coordinate margin, and scale-down only when the minimum does not fit
On a `canvasSize` surface, the lattice's drawn square pitch is:

```
pMin = max(colPitch, labelClearancePitch)      (the derived minimum, unchanged)
avail = canvasSize − 2 × (gutter > 0 ? gutter : 8)
pFit = floor(min(avail / cols, (avail − LABEL_BAND) / rows))
p    = max(pMin, min(pFit, 1.5 × colPitch))
```

Then:
- The field is padded symmetrically on both axes up to the square (`S − 2 × gutter`). The dot field paints that coordinate margin at pitch `p`.
- When `p = pMin` still does not fit, `S` grows to the required side and the whole drawing scales down uniformly, as the current rule already allows.
- The gutter / pitch loop reuses the existing fixed-point iteration in `layoutGeometry` (the gutter depends on edge lengths, which depend on `p`).

Results:
- The reported 3×3 wilderness core without gateways draws at `p = 59`: 177 of 208 px wide instead of 120 of 206.
- A single node draws at `p = 60` (the 1.5× cap) inside about 3.5 cells of dot field.
- The reported 3×3 shape with named edge markers keeps `p = 40` and scales to `208 / 222.91 ≈ 0.933`, so its node labels draw at about 8.40 CSS px.

Why pitch rather than magnification:
- Marker radii, the 9-unit label size, and the 10-unit marker-name size stay exactly as declared. The rule "a node label never draws larger than the surface's chrome step" and the rule "scale never exceeds 1" both still hold with no exception.
- The non-overlap invariant still holds, because the pitch only grows from its derived minimum.
- The dot field stays registered to the pitch on both axes.
- Cells stay square.

*Why the 1.5× cap:* without it, a one-node lattice's cell would be 178 units. The dot field would collapse into the single dot under the marker, and the presence band that pins that layer would fail.

*Alternative:* uniform magnification to fit the bounding box. Rejected, because it inflates labels above the island's 10px chrome step (a 3×3 at about 1.43× draws 12.9px labels) and brings back the retired upscale bound.

*Alternative (design §11 wording "keeps the current node centred when the box exceeds the minimap"):* crop a 208 window around the current node. Rejected for this slice for three reasons:
- The shipped grid maps use `map_visual_range: 2` (`world/maps/altoria_capital.py`, `village_ciaran.py`). A 5×5 lattice would clip half of its outer ring.
- Edge markers are placed where a bearing leaves the drawn extent. Under a crop they would have to be recomputed against a moving window.
- Uniform scale-down keeps every in-view node visible at about 0.9 scale for those maps.

The full map (C2) is the surface for large lattices. This deviation from the design doc is deliberate and is recorded here.

### D4. Graph fill: crop to the drawn footprint and never magnify
On a `canvasSize` surface, the radial placement's canvas (side `L`, current node at `L/2`) is shown through a square viewBox:
- centred on `(L/2, L/2)`
- of side `S = max(canvasSize, L − 2 × RADIAL_GEOMETRY.PAD + 16)`

That is the model's footprint bounding box plus an 8px inset. Results:
- A one-ring interior (`L = 244`) draws at `208 / 212 ≈ 0.98` instead of `208 / 244 ≈ 0.85`.
- A two-ring interior draws at about 0.58. The overlay is the readable surface for it.
- A current-only interior (`L = 100`) draws its single node at scale 1 in the centre of the square.

It is not magnified, for the same label-size reason as D3. That is the truthful picture of a one-room view, and the island's constant size means the empty panel costs nothing.

The overlay, with no `canvasSize`, keeps drawing the full radial canvas at `markerScale`.

### D5. Remembered nodes on the graph variant: an island mirror and an overlay list
The island's visible remembered list is deleted. The spec's readability contract is met in two places:
- **Island (assistive technology).** A visually-hidden, non-focusable `<ul data-testid="local-map-remembered-mirror" aria-label="記得的地點">` has one entry per `remembered` node in payload order, each giving its untruncated label. There is no octant, because a graph asserts no bearing. It reuses the `.visually-hidden` rule and the `:not(.visually-hidden)` exclusion already written for the edge-marker mirror.
- **Full-map overlay (sight, one activation away).**
  - On the graph variant, `MapOverlay.vue` renders `<ul class="map-overlay__remembered" data-testid="map-overlay-remembered">` below the canvas. Each entry pairs the remembered diamond indicator (`aria-hidden`) with the full label as visible text.
  - Entries have no `tabindex`, no role, and no activation.
  - The island's full-bleed affordance already opens this surface in one activation, which is the same disclosure path the spec already uses for marker names the island truncates.

Out of scope for this change:
- On the lattice variant, the overlay keeps presenting remembered nodes only as named edge markers.
- Remembered nodes are still never placed on a graph canvas.

*Alternative:* a mirror only. Rejected, because a sighted reader who does not use assistive technology could not read a remembered room's name anywhere.

*Alternative:* collapse the island list into a "+N" disclosure. Rejected. It adds a second tab stop to an island whose contract is exactly one.

### D6. The full log opens at its last line
In `FullLogOverlay.vue`, `focusSelf()` sets `overlayEl.scrollTop = overlayEl.scrollHeight` after `trap.enter()`. `openFullLog()` in `composables/use-overlays.js` already calls `focusSelf()` after `nextTick()`, so the lines are laid out when it runs. Nothing watches `lines` while the log is open, so a reader who scrolled up is never pulled back down.

The requirement is ADDED to `webclient-input-narrative`, the capability design §14 assigns to log reading, rather than MODIFIED into the contextual-hud caption requirement. C4 and C6 replace that caption requirement, and a separate requirement survives them unchanged.

### D7. Spec deltas and archive order
- `webclient-local-map`: the one large requirement is MODIFIED with its title unchanged, so every existing `covers_requirement` annotation stays valid.
  - `openspec validate` rejects a MODIFIED block that drops an existing scenario name, so every scenario title is kept, and the obsolete ones get new bodies that pin the new behaviour. "A long remembered list keeps required island content in view" now asserts that no list is laid out and the size is unchanged. "The height budget is spent as an equivalent width bound" now pins the generic cap rule for surfaces with no square canvas. "Repeated budget measurements do not ratchet the canvas down" now asserts that nothing is measured. "The full-map overlay omits the remembered-node list and the readout line" is now scoped to the lattice variant.
  - Restated scenarios, with new numbers where geometry changed: the island fill / coordinate-margin, name-band, sparse-payload, type-ladder, pitch, content-containment, gutter, readout-box, and interior-rooms scenarios.
  - New scenarios: "The full-map overlay lists a graph payload's remembered rooms", "The island's size never depends on the payload", and "A graph payload is cropped to its footprint and never magnified".
- `webclient-contextual-hud`: the minimap-convention requirement is MODIFIED. Only the remembered-node presentation clause changes.
- `webclient-input-narrative`: one ADDED requirement.

This is the first change in the series, and no earlier series change touches these requirements. C2 (`webclient-full-map-fit-view`) and C4 (`webclient-avg-stage-shell`) must write their MODIFIED text on top of this change's versions and be archived after it.

## Risks / Trade-offs

- [Some payloads now draw smaller than before. The reported wilderness with gateways draws node labels at about 8.40 CSS px (was 8.87), and two-ring interiors draw at about 0.58] → Both stay non-overlapping and are one activation from the full map. The fixed square is the requested trade.
- [Pitch-fit changes pinned numbers in `map_lattice_fidelity.test.js` ("Design D5 Table") and in the browser geometry tests] → Tasks 4.x and 5.x re-derive every pinned figure from D3 / D4 and name each test.
- [A future C4 anchor might be narrower than 218px] → The card width is `208 + 2 × 4 + 2 × 1` and does not depend on the anchor. C4 sizes its `map` anchor from it.
- [Removing `maxHeight` from the island leaves `latticeStyle`'s height-cap branch used only by bare mounts, whose default is `maxHeight: 296`] → Kept on purpose as the generic cap path. C2 may reuse or delete it when it rewrites overlay sizing.

## Migration Plan

None. The client is unreleased, and nothing is stored.
