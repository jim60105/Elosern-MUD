# The Overlay's Marker Names Obey the Geometry That Reserves Them

## Why

`webclient-minimap-05-edge-markers-replace-list` made the edge direction marker
the *presentation* of a remembered gateway and, in the same pass, widened the
name-fitting rule to cover both surfaces: "On every surface that draws edge
direction markers — **the island as well as the full-map overlay** — … each name
SHALL be fitted to the free span its own marker holds along its edge … Where a
name does not fit its span it SHALL be truncated with an overflow indicator"
(`openspec/specs/webclient-local-map/spec.md:352`). The island implements that.
The overlay does not: `MapLattice.vue`'s `fittedEdgeMarkers` returns early for
`overlayChrome` and draws `marker.name` — the untruncated payload label — with
no span measurement, no truncation, and no anti-ambiguity pass.

That leaves the renderer drawing something the placement model was told would
not exist. The overlay hands `edgeMarkersFor` a declared name box of
`nameWidth = (labelMax + 1) × 11 = 121` user units, and the model reserves the
band and the along-edge slots on that promise:

| quantity | value | what it is |
| --- | --- | --- |
| `slotMinH` | 123.95 | `max(2·reach + 1, nameWidth + 2)` — the along-edge slot floor |
| `namePad` → `outset` | 123 → 184.48 | the outward depth a left/right name box may occupy |
| `gutterMin` | 246.95 | the band that keeps names off the canvas rect |

Both terms resolve to the **same 11 glyphs at the overlay's 11-unit name step**,
because `nameWidth` *is* `(labelMax + 1) × 11`. A name longer than that overruns
whichever bound governs its edge — the slot on `top`/`bottom` (the name is drawn
along the edge, centred), the band on `left`/`right` (the name is drawn outward,
perpendicular). Neither overrun is caught by anything: the model cannot see the
drawn string, and no test measures it.

It is not hypothetical. The presenter composes a remembered gateway's label as
the far-side anchor display name, qualified with the boundary node's canonical
name when two gateways share a far side (`local_map.py:518`). The longest
authored region name today is 「西部丘陵與谷地」 (7), and the shipped gates are
「南門」/「北門」 (2), so the worst case in current content is
「西部丘陵與谷地（南門）」 — **exactly 11 glyphs, exactly the reserved capacity,
with zero headroom**. One more glyph in either half, in any future authored
region or gate name, overflows. With markers crowded on one edge the threshold
falls further: at 6 markers a 13-glyph name overruns its slot, and at 7 or more
the slot floors at 124.01 units and a 12-glyph name overruns.

## What Changes

- The overlay's `overlayChrome` early return in `fittedEdgeMarkers` is deleted.
  **Both** surfaces run one fitting pass, parameterized by the surface's own
  declared name step and name box rather than by a branch on which surface is
  drawing.
- **The renderer stops re-deriving the model's slot arithmetic.**
  `fittedEdgeMarkers` currently recomputes `namePad`, `inset`, `slotMinH` and
  `slotMinV` itself, with the island's numbers baked in as literals — `namePad`
  is hardcoded `18`, which is `max(nameWidth, nameHeight) + 2` only because the
  island declares `nameWidth: 0`. On the overlay's declared box those literals
  give `inset = 141.95` against the model's real `246.95`, so simply deleting the
  branch would fit the overlay's names against spans that do not exist. Instead
  `edgeMarkersFor` returns each marker's own free span along its edge — a value
  it already computes to place the marker and currently discards — and the
  renderer reads it. This is the only edit to
  `web/static/webclient/js/elosern/local_map.js`: one additive field, no changed
  placement, and it deletes the duplicated formulas rather than parameterizing a
  second copy of them.
- The fit budget becomes the **lesser of the two bounds the model was already
  given**: the free span the marker holds along its own edge, and — on a surface
  that declares an outward name box — that box's own capacity. In the overlay's
  numbers that is `min(⌊span / 11⌋, labelMax + 1)`; on the island, which declares
  `nameWidth: 0`, the outward term does not exist and the span remains the only
  bound, exactly as it is today. No new constant is introduced: `labelMax + 1` is
  the number `nameWidth` already encodes.
- **BREAKING** (spec-level; the project is pre-release with zero users, so there
  is no migration): an overlay marker name longer than the surface's declared
  capacity is now **truncated with the same head-and-tail ellipsis the island
  uses**, instead of being drawn at full length past its reserved box. The
  overlay's `labelMax` of 10 already governs its node labels; its marker names
  now honour the same legibility contract rather than being the one text on the
  surface that obeys no bound.
- The anti-ambiguity invariant — never draw two equal names for two differing
  payload labels — now runs on the overlay too, because truncation makes
  collisions reachable there for the first time. A marker whose name cannot be
  distinguished keeps its diamond, its bearing, and its landmark ring, and its
  untruncated label stays available as its accessible name (the overlay already
  carries `aria-label="{marker.name}"`).
- The overlay declares its marker-name type size the way it declares every other
  size it draws: `MapOverlay.vue` passes `:marker-name-font="11"`, the overlay's
  `<text>` binds that number inline, and `layoutGeometry`'s reserved name box
  becomes `(labelMax + 1) × markerNameFont` instead of `(labelMax + 1) × 11`.
  `11` is what `.local-map__edge-marker-name` and that expression both hardcode
  today, so **no drawn size and no reserved geometry changes** — but the number
  that sizes the glyph, the number that budgets the fit, and the number that
  reserves the room become one number, which is the invariant this change exists
  to establish.
- **ACCEPTED REGRESSION**: for a label longer than the full-map surface's declared
  capacity, a sighted keyboard-only reader running no assistive technology no
  longer has a surface that shows the whole name — the overlay marks the
  truncation with the overflow indicator and the untruncated label is carried only
  as the marker's accessible name. The shipped scenario promised otherwise, but
  that promise was never deliverable in the case it now fails: an over-capacity
  name does not render whole, it renders *past its reserved box*, overprinting a
  neighbouring name or — on a left/right edge — the canvas rect and the node
  markers, labels and axis the same requirement forbids it to intersect. The
  delta spec states this as its own scenario rather than leaving it implicit. It
  is prospective: today's longest authored label is exactly at capacity.
- The **full-map surface stays the disclosure path** that design D8 of change 05
  named it. Its capacity (11 glyphs) remains strictly larger than the island's
  span-limited budget (5–6 glyphs on the reported payload), so every name the
  island truncates or drops still reads longer on the overlay. What changes is
  that the overlay's disclosure is now bounded and stated, rather than unbounded
  and unenforced.

Out of scope:

- Growing `nameWidth` so that any authored label fits without truncation. That
  is the rejected alternative in design D2: it lets one long label inflate the
  gutter and shrink the drawn lattice for every payload.
- The island's own fitting, its type ladder, its assistive-technology mirror,
  and the coordinate-field layers. All shipped and unchanged.
- The `local_map` v1 payload, the server presenter, both validators, and the
  overlay host's focus-trap contract. The preserved UMD render model gains one
  additive field and no behaviour change; its dependency-free Node gate stays
  dependency-free.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: "The browser minimap renders states without relying on
  color alone" — the marker-name clause gains the rule that the fit budget is the
  lesser of the along-edge free span and the surface's declared outward name box,
  so a drawn name can never exceed the geometry the placement helper reserved for
  it; and the anti-ambiguity invariant is stated as binding on every surface that
  fits names, not only on the island.

## Impact

- Affected code: `web/webclient-app/components/MapLattice.vue` (the
  `overlayChrome` early return in `fittedEdgeMarkers` removed; the duplicated
  slot arithmetic replaced by the span the model now returns; the budget's second
  term; the overlay `<text>`'s inline size binding; the hardcoded `font-size`
  dropped from `.local-map__edge-marker-name`),
  `web/static/webclient/js/elosern/local_map.js` (each returned marker gains its
  own `span`, computed from values the function already holds), and
  `web/webclient-app/components/MapOverlay.vue` (one declared prop).
- Not edited: `web/webclient-app/components/LocalMap.vue`,
  `web/webclient-app/styles/tokens.css`,
  `web/webclient/presentation/local_map.py`, and both payload validators.
- Affected tests: `web/webclient-app/tests/world/map_lattice.test.js` (the
  overlay's fitted names, the capped budget on both edge orientations, the
  overlay anti-ambiguity case, and the island's existing budget proven
  unchanged), `web/static/webclient/js/tests/local_map.test.js` (the returned
  span's agreement with the marker placement, at both surface geometries),
  `web/webclient-app/tests/overlays/map_overlay.test.js` (the overlay's declared
  props), and
  `web/tests/browser/test_browser_local_map.py` (a crowded-edge overlay gate
  asserting no two drawn marker-name boxes intersect).
- The modified requirement title is modified in place with no rename, so every
  existing `@covers_requirement` anchor on
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  stays valid.
- No server, protocol, store, or payload change; no player-facing command
  changes, so `docs/game/commands.md` is untouched.
