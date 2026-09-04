# Design — Draft Lattice Fidelity

## Context

The minimap island (`web/webclient-app/components/LocalMap.vue`) draws its map
through the shared renderer `MapLattice.vue`, which `MapOverlay.vue` also mounts.
The island's card is a **210px content box** in the 230px `hud-right` column; the
renderer's width cap is `maxWidth: 206`, its canvas ground is `--ink-860`
(`#151219`), and its lattice geometry today is `colPitch 58`, `rowPitch 44`,
`labelMax 4`, node labels at `font-size: 11` in SVG user units, `markerScale 1`.

Four sibling changes are this change's baseline, and this delta builds on their
text, not on the shipped text:

- `webclient-minimap-03-canvas-scale-and-budget` — the canvas claims the island's
  content width, the height budget is a fixed point measured from geometry the
  canvas does not move, and every cap resolves into one floored width bound
  `min(maxWidth, maxHeight × canvasWidth / canvasHeight, canvasWidth × maxUpscale)`
  with the island at `maxUpscale: 2`. Its design **D7 explicitly defers to this
  change**: "this change's `maxUpscale` viewBox approach is expected to be
  superseded there", along with "pitch versus scale, the label/pitch font ratio,
  the far-field dot field, the fog vignette, and the axis cross".
- `webclient-minimap-04-island-single-affordance` — the island's only affordance is
  a full-bleed transparent `<button>` beneath the content; the readout is
  coordinate-only and holds no hover/selection state.
- `local-map-remembered-are-map-gateways` — `remembered` on `grid`/`wilderness`
  becomes a stood-on map boundary, and a **flagged, strikeable** ADDED requirement
  ("The map surfaces state a place name only where it adds information") makes the
  shared renderer "NOT draw visible label text for an in-view node whose label
  string is identical to the `current` node's label string".
- `webclient-minimap-05-edge-markers-replace-list` — the island's remembered list
  is deleted on the lattice variant; each edge marker carries its name inside a
  **44.46-unit gutter band** declared as `nameWidth 0, nameHeight 16`, and that band
  "lies outside the canvas rect containing every node marker, every node label,
  **and the axis**".

The draft this change closes the gap to is `.lay-grid` inside
`docs/design/elosern-redesign/index.html`, `viewBox="0 0 180 150"`, rendered by
`.mini svg { width: 100%; max-width: 172px }`:

| draft element | value | in the island's rendered pixels |
| --- | --- | --- |
| `<pattern id="mgrid" width="24" height="24">`, `circle r="1.15" fill="#3a3344" fill-opacity=".85"` | dot pitch 24 = node pitch 24 | cell 22.93 px, dot r 1.10 px |
| `<radialGradient id="mfog" cx="90" cy="75" r="112">`, stops .5/0 · .78/.38 · 1/.72 | knowledge edge | — |
| axis `<g stroke="#3a3344" stroke-width="1.5" opacity=".65">`, full width and height through the current node | the drawn form of 「北↑ 東→」 | 1.43 px |
| node labels `font-size="8"` | 4.44% of canvas width | 7.64 px, against 10px chrome |
| canvas | 180 × 150 = 7.5 × 6.25 cells | 172 × 143 px |
| node core (3 × 3 at pitch 24) | 72 × 48 = 40% of canvas width | 68.8 × 45.9 px |

`REDESIGN.md` §7.1's table classifies the vignette as "knowledge edge (not
terrain)" on both layouts and reserves the header mark `北↑ 東→` for the lattice
because "a graph asserts no axis". §7.4 closes with the sentence this change
exists to honour: "Lattice dot-field and axis cross are tuned to be plainly
visible (`#3a3344` at 0.85 dot fill-opacity, 1.5px axis at 0.65) — the lattice's
geometry is its claim, so it must not be invisible; implementation waves pin
their presence and contrast."

## Goals / Non-Goals

**Goals:**

- The lattice's coordinate claim is visible: one dot per coordinate cell,
  registered to the placement, with its presence and contrast pinned as a band so
  neither an invisible layer nor an over-loud one can ship.
- The canvas edge reads as the limit of knowledge, in one treatment per surface,
  with no fabricated terrain geometry anywhere.
- The axis is drawn wherever, and only wherever, the surface states its convention
  in words.
- The type hierarchy is right side up: a node label is never larger than the
  island's own chrome, at any payload, and a sparse payload reads *airy* rather
  than *magnified*.
- The cell-count proportion moves toward the draft's, by the only honest lever —
  the pitch derived from what actually needs clearing — with the non-overlap
  invariant still constructible at every placement the model can produce.
- `MapOverlay.vue` is not edited and provably cannot regress.
- `web/static/webclient/js/elosern/local_map.js` is not edited.

**Non-Goals:**

- What counts as `remembered` (`local-map-remembered-are-map-gateways`).
- The island's affordance and its coordinate readout
  (`webclient-minimap-04-island-single-affordance`).
- The edge markers' name geometry, their fit-to-span truncation, and the
  assistive-technology mirror (`webclient-minimap-05-edge-markers-replace-list`).
- Pan, zoom, per-cell terrain, a terrain baseline, or any drawn shape the payload
  does not back.
- The payload, the presenter, both validators, and the Node gate's behaviour.

## Decisions

### D1 — The dot field is the coordinate space, registered to the placement

The field is one `<rect>` filled with a `<pattern patternUnits="userSpaceOnUse">`
whose tile is the drawn cell — `width = colPitch`, `height = rowPitch` — carrying
a single circle. Two properties make it a claim rather than a texture, and both
are pinned in the requirement:

1. **Pitch.** The tile's width and height are the *drawn* column and row pitch, so
   one dot spacing is exactly one coordinate cell on each axis. If a later change
   moves the pitch, the field moves with it or the requirement is violated.
2. **Registration.** The tile's circle is offset so a dot falls exactly on each
   node-lattice position: for a node at `col × pitch + pitch/2 + originOffset`,
   the in-tile offset is `(pitch/2 + originOffset) mod pitch`. So for **every**
   drawn node, a dot position coincides with its centre — the testable form of
   "the dot marks a cell, and a node marker occupies the cell it is drawn on".
   An occupied cell shows its marker (the field is painted first, beneath
   everything), so no cell ever shows both a dot and a marker.

The dot's radius is `1.15 × markerScale` — the draft's literal radius at the
draft's own scale, scaled with the marker ladder exactly as every other marker
geometry is, so the field's relation to the markers is identical on the island
(r 1.15) and in the overlay (r 5.55).

*Alternatives rejected:*

- **A dot at every cell *corner* instead of the cell centre.** Reads as a
  surveyor's grid and is arguably prettier, but it makes the "one dot = one cell"
  claim unverifiable against the placement: no drawn node ever coincides with a
  dot, so nothing pins the registration and a half-cell drift would be invisible.
  The draft itself registers on centres (`cx=18, cy=3` on a 24 tile puts dots at
  x = 18 + 24k, i.e. exactly the draft's node columns 66 / 90 / 114).
- **Drawn `<line>` grid rules instead of dots.** Rules at the cell pitch would be
  indistinguishable in weight and colour from connector edges — the topology
  layer — which is the one thing the field must never be confused with.
- **A CSS `background-image` gradient grid on the SVG element.** Cheapest, but it
  cannot be registered to the placement (the SVG's CSS background is in element
  pixels, the placement is in viewBox units, and the scale is payload-derived), and
  it paints under the SVG content so the vignette could not dim it — see D3.
- **A `<g>` of individual `<circle>` elements.** One element per cell, up to
  ~29 on the island and hundreds in the overlay, all of them boxes a future DOM
  audit could accidentally pair. One `<rect>` plus a `<pattern>` is one box.

### D2 — Presence and contrast are pinned as a band, not as a WCAG threshold

§7.4 requires the field and the axis to be visible; a naive reading would demand
the 3:1 of WCAG 1.4.11. The measurements say that is the wrong instrument here.
Relative luminance against the island's `--ink-860` (`#151219`) canvas ground:

| layer | composite | contrast |
| --- | --- | --- |
| dot field, `--ink-edge` at 0.85 fill-opacity | `#342e3c` | **1.42:1** |
| axis, `--ink-edge` at 0.80 opacity | `#332c3b` | **1.39:1** |
| axis at the draft's 0.65 opacity | `#2d2735` | 1.29:1 |
| connector edge, `--ink-edge` at full opacity (the reference) | `#3a3344` | **1.53:1** |
| a dot raised to 3:1 | ≈ `#655e78` | 3.02:1 |

The last row is the argument. Reaching 3:1 needs a dot **brighter than the
connector edges** — decoration louder than topology, and brighter than the
`visible_visited` marker's own ink fill. That inverts the drawing's hierarchy to
satisfy a threshold that does not apply: these layers are decoration whose claim
is carried redundantly elsewhere (the node placement itself, the header's
`北↑ 東→` marks, and the readout's coordinate figure), so no information is
available only through them.

The requirement therefore pins a **band** instead of a threshold, and the band is
what makes both failure modes testable:

- a **floor** of 1.15:1 at every point of the canvas and 1.35:1 within the
  un-fogged inner field — so "the layer shipped at zero opacity", "the layer
  shipped at the ground colour", and "the layer was deleted" all fail;
- a **ceiling** at the connector-edge ink's own contrast against the same ground —
  so the field can never out-read the topology it decorates;
- a **presence** assertion independent of colour: the element exists, is painted,
  and its resolved fill differs from the canvas ground.

Chosen values: dot at 0.85 fill-opacity (the draft's own), axis at **0.80**
(raised from the draft's 0.65, which measures 1.29:1 — below the 1.35 inner
floor; 0.80 measures 1.39:1 and still sits below the connector edge's 1.53:1).

*Alternatives rejected:*

- **Raise both layers to 3:1.** Priced above; inverts the hierarchy.
- **Spec "plainly visible" as prose with no number.** That is exactly the state
  §7.4 complained about, and it is what let four waves ship nothing.
- **Add `--map-lattice-dot` / `--map-lattice-axis` tokens.** `tokens.css` adds a
  map token only where "the tokens above lack" the value; `--ink-edge` **is**
  `#3a3344`, the draft's own dot and axis ink, and reusing it means a future
  change to the ink family moves the decoration and the edges together, which is
  correct. Zero new tokens is also zero new contrast surface to audit.

### D3 — The vignette is the knowledge edge, and the draft's own outer stop erases what it is meant to reveal

The vignette is a single full-canvas `<rect>` filled with a radial gradient,
painted **over the dot field and beneath every connector edge, node marker, node
label, and axis line** — the draft's own paint order. It is not per-cell, not
per-region, and traces no feature: one element, one gradient, no geometry. That
keeps §7.1's "knowledge edge (not terrain)" literally true and follows the
overlay's `mapcanvas` precedent, which paints "a dark radial-gradient background
… with pure CSS (no fabricated terrain geometry)".

It is an SVG rect rather than a CSS background because a CSS background on the
SVG element paints *beneath* the SVG content, which would leave the far-field
dots undimmed — and 「四週遠處的淺色格點」 is precisely the owner's ask: the far
dots must be *paler*, not merely present.

The measurement then forces one departure from the draft. Compositing the dot over
the fogged ground (`--map-canvas-lo`, `#0c0a10`, within 3/255 per channel of the
draft's `#0e0b13`):

| vignette opacity at that point | ground | dot | dot contrast |
| --- | --- | --- | --- |
| 0.00 (inner field) | `#151219` | `#342e3c` | 1.42:1 |
| 0.26 | `#131017` | `#2b2632` | 1.25:1 |
| 0.50 (chosen outer stop) | `#100e14` | `#201c26` | **1.15:1** |
| **0.72 (the draft's outer stop)** | `#0e0c12` | `#171418` | **1.07:1** |

At the draft's 0.72 the corner dots measure 1.07:1 — the fog deletes the
far-field dots the change exists to add. The stop **offsets** stay the draft's
(.5 / .78 / 1) and the opacities are scaled to **0 / 0.26 / 0.50**, so the
gradient keeps the draft's shape and every dot on the canvas clears the 1.15:1
floor. The requirement states this as a property — the vignette SHALL NOT reduce
the dot field below the floor at any point — rather than as the number, so it
survives a later change of ground colour.

*Alternatives rejected:*

- **Keep 0.72 and brighten the dot instead.** A mid-grey dot (`#646464`) still
  measures only 1.28:1 at the 0.72 corner while being wildly louder than the
  markers everywhere else. Under a 0.72 wash there is no dot colour that is both
  visible at the corner and quiet at the centre.
- **Paint the vignette beneath the dot field.** Then the far dots are not faint,
  and the layer stops meaning "receding knowledge".
- **Mask the dot pattern with a radial gradient instead of washing over it.**
  Visually equivalent to a wash but adds an SVG `<mask>` — the least uniform
  corner of the platform for this purpose — and the far field would then fade to
  the ground rather than to the vignette ink, which is a *weaker* edge.
- **Give the overlay a second vignette on top of `mapcanvas`.** Priced in D9.

### D4 — Font proportion and cell-count proportion: the pitch is derived from what needs clearing

This is the load-bearing decision, so it is worked from the constraints.

**Why 58 exists.** `2026-08-27-fix-webclient-local-map-node-crowding` derived it
from one clearance: "the column pitch must clear two truncated node labels (4 CJK
chars at 11px monospace ≈ 44px wide) centered under horizontally adjacent nodes
with a strictly-positive visible gap". The worst-case truncated label is
`labelMax + 1 = 5` full-width glyphs, i.e. `5 × 11 = 55` units, so
`58 = 55 + 3`. That same fix **rejected** "truncate labels more aggressively
(fewer characters) instead of widening the column pitch" as making short place
names unrecognizable. Both facts are respected here: `labelMax` stays **4**, and
the lever pulled is the pitch and the type size, not the glyph count.

**Why 58 forces the draft's density out of reach.** At a rendered canvas of
206px, cells across = 206 / rendered pitch. The draft's rendered pitch is 22.93px
(7.5 cells); a 58-unit pitch drawn at scale 0.784 renders at 45.5px (4.53 cells).

**What the gateway change unlocks.** `local-map-remembered-are-map-gateways`
makes the renderer draw no visible label for an in-view node whose label repeats
the current node's. On the reported wilderness payload — current cell plus eight
neighbours, all in one region, all sharing the region display name — **exactly one
label is drawn**. With most cells unlabelled, "two truncated labels side by side"
is not a case the payload produces, so the constraint that produced 58 does not
bind. The pitch becomes a function of the drawn label set.

**The clearance model.** Conservative footprint halves at `markerScale 1`:
current circle `r 8` + 2px stroke → **9**; visited/unvisited dot `r 4.5` +
stroke → **5.5**; landmark ring `r 5`; actionable halo `r 10` + 2px stroke →
**11** (the widest, and drawn on every actionable neighbour). Conservative line
box for a label at font `F`: `0.95F` above the baseline, `0.45F` below. The
browser geometry audit requires a **≥2-unit** gap between every pair of boxes, so
2 is the gap constant, not 1.

With `F = 9` and the label baseline at **22** units below the node origin
(down from 26):

```
label box                     = [22 - 8.55, 22 + 4.05]  = [13.45, 26.05]
own-node clearance            = 13.45 - 11 (halo)       = 2.45  >= 2   OK
two adjacent halos            = 2 x 11 = 22             <  pitch
visible connector segment     = pitch - 26              >  0
next row's footprint top      = pitch - 11
    requires pitch            >= 11 + 26.05 + 2         = 39.05
two adjacent DRAWN labels     = 2 x (5 x 9)/2 = 45 wide
    requires pitch            >= 45 + 2                 = 47
```

So there are exactly **two** clearance regimes, and the renderer picks between
them from the drawn label set:

```
pitch = max( declaredPitch,
             adjacentDrawnLabelPair ? (labelMax + 1) * labelFont + 3 : 0 )
```

- island `declaredPitch = 40` (the 39.05 floor rounded up, 0.95 units of slack),
  **square on both axes**;
- island labelled regime `= (4 + 1) × 9 + 3 = 48`, also square;
- overlay `colPitch 280 / rowPitch 212` with the labelled term
  `(10 + 1) × 11 + 3 = 124` — below both, so it never binds and the overlay's
  geometry is bit-identical (D9).

**Why the label is 9 units.** The draft's label is 4.44% of its canvas width;
9 units on the island's 206-unit canvas is 4.37%. It is also the number that puts
the drawn label under the island's own chrome: with the uniform scale now capped
at 1 (D5), the drawn label is **at most 9 CSS px** against the header's 10px
type step, where today a sparse payload draws 22 CSS px. Nothing gets less
legible: the reported payload's label goes from 8.62 px (11 units at scale 0.784)
to **8.87 px** (9 units at scale 0.986), and both are larger than the draft's own
7.64 px.

**Why the pitch stays square.** A rectangular cell distorts direction: a node at
`(+1, +1)` draws at `atan(rowPitch / colPitch)` from horizontal, while its
edge-direction ray is computed from the **raw** coordinate delta and therefore
points at 45°. Today's `58 × 44` draws that node at 37.2° — a 7.8° disagreement
between the lattice and the marker layer. A square pitch makes the disagreement
**zero**, so the lattice and the markers finally point the same way, and the draft
is square too. The cheapest route to the draft's 7.5 cells — `colPitch 27.5` with
`rowPitch 44` — would triple the error to 13°, draw a visibly stretched field
where the draft's is square, and make the island disagree with the overlay about
the shape of a cell. Density bought that way costs more than it buys.

**What this yields, and what it does not.** On the reported payload (3 × 3
in-view, remembered gateways present, so change 05's 44.46-unit band applies):

| | shipped | this change | draft |
| --- | --- | --- | --- |
| pitch (user units) | 58 × 44 | **40 × 40** | 24 × 24 |
| canvas (user units) | 262.91 × 234.91 | 208.91 × 222.91 | 180 × 150 |
| uniform scale | 0.784 | 0.986 | — |
| rendered pitch | 45.5 px | **39.4 px** | 22.9 px |
| cells across | 4.53 | **5.22** | 7.50 |
| dots drawn | 0 | **~29** | ~47 |
| node label | 8.62 px | **8.87 px** | 7.64 px |
| node core / canvas width | 66% | **57%** | 40% |

The draft's 7.5 cells is **not** reached, and the arithmetic above says why: the
row floor is 39.05 units, so a 206-unit canvas cannot carry more than 5.28 cells
across while a label sits below a marker and clears the next row's actionable
halo. Reaching 7.5 requires a 27.5-unit pitch, which needs the label box to end
by `27.5 - 11 - 2 = 14.5` units while it cannot start before `11 + 2 = 13` —
1.5 units for a line box that needs 12.6 at `F = 9` and 11.2 at the draft's
`F = 8`. **The draft's density and our non-overlap SHALL are not simultaneously
satisfiable**; see D8 for how the draft gets away with it and what is matched
instead. The two levers that would close the remaining gap are named rather than
taken: shrinking the actionable halo (worth 39.05 → 35, i.e. 5.9 cells, at the
cost of a pointer target already only 20px across) and dropping node labels from
the island entirely (worth the draft's density outright, at the cost of a spec'd
clause and of the draft's own drawn labels). Both are separable follow-ups.

*Alternatives rejected:*

- **Truncate labels harder (derive `labelMax` from the pitch).** `floor(27.5/9) - 1
  = 2` glyphs plus an ellipsis. Explicitly rejected by the archived crowding fix,
  and it recreates change 05's ambiguity defect on the node layer: 「西部…」 twice.
- **Suppress a label because it *collides* rather than because it *repeats*.**
  Would reach any density, but it hides distinct information for a geometric
  reason. The gateway change's suppression is sound because the suppressed string
  adds nothing; suppressing a different name loses a fact. Kept as the fallback of
  last resort only if the flagged sibling requirement is struck (D11).
- **Stagger `text-anchor` outward on horizontally adjacent labels**, as the draft
  does. It reduces but does not remove the overlap (D8), and it detaches a label
  from the cell it names.
- **A single always-48 square pitch, no regime switch.** Simpler, and still an
  improvement (4.86 cells, label 7.96 px), but it spends the whole gain of the
  gateway change to avoid one `max()`. Kept as the strike fallback (D11).
- **Keep `rowPitch 44` and shrink only the column pitch.** Rectangular cells;
  priced above.

### D5 — The width fill becomes coordinate margin, and `maxUpscale` retires

Change 03 honoured the draft's `.mini svg { width: 100% }` by scaling the whole
viewBox up, bounded at `maxUpscale: 2`. Under a uniform upscale the
label-to-canvas ratio is *preserved* rather than corrected, so a sparse payload
gets a magnified drawing: a one-node payload's 58 × 58 canvas drawn at 116px is a
2× ramp — a 22px label and a 32px "you are here" seal in a card whose own title is
10px.

The alternative this change takes is to spend the slack on **coordinate space**
instead of on magnification. The canvas's drawn extent is padded symmetrically
around the node core up to the surface's width cap; the edge-marker band stays the
canvas's outermost band, and everything between the core and that band is
coordinate margin that the dot field paints. Composed with change 03's single
width bound, that has one clean consequence:

```
core    = cols * pitch                     (node core width, user units)
g       = the model's marker gutter        (44.46 with names, 26.46 without, 0 with no markers)
fieldW  = max(core, maxWidth - 2g)         (the padded field rect)
marginX = (fieldW - core) / 2
W       = fieldW + 2g                      (= maxWidth whenever core + 2g <= maxWidth)
marginY = min(marginX, max(0, (maxHeight - coreH - band - 2g) / 2))
H       = coreH + band + 2 * marginY + 2g
bound   = min(maxWidth, maxHeight * W / H)
scale   = bound / W = min(maxWidth / W, maxHeight / H)  <= 1
```

`scale = 1` whenever the drawing fits both caps, and below 1 only when it does
not. **The drawing is never magnified above its designed size**, so there is
nothing left for an upscale bound to bound: `maxUpscale` is removed, and
`widthCaps()` loses its third term. `MapOverlay.vue` never passed the prop, so its
removal cannot reach the overlay.

Two properties make the padding free rather than a cost, and both are pinned:

- Padding **never reduces the uniform scale** below what the unpadded canvas would
  have achieved. When the width binds, the rendered core is `maxWidth × core / W`,
  which equals `core` exactly once `W = maxWidth`. When the height binds, the
  rendered core is `maxHeight × core / H` — independent of `W`, so padding the
  width is a no-op in that regime. The vertical margin is the safeguard on the
  other axis: it is capped at the horizontal margin **and** at the point where the
  height cap stops being slack (`H ≤ maxHeight`, since with `W = maxWidth` the
  height term `maxHeight × W / H` binds exactly when `H > maxHeight`). A tall
  payload therefore takes **no** vertical margin at all, and cannot lose scale to
  it.
- The **marker band stays outermost**: the padded field rect, not the bare node
  rect, is what the placement helper is told the canvas is, so the markers sit on
  the outer border with the coordinate margin inside them (D10).

Worked, at the island's `maxWidth 206` and a 296px height cap:

| payload | `core` | `g` | `marginX` / `marginY` | canvas W × H | scale | rendered label | cells across |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 × 3, remembered present | 120 | 44.46 | 0 / 0 | 208.91 × 222.91 | 0.986 | 8.87 px | 5.22 |
| 3 × 3, no remembered | 120 | 0 | 43 / 43 | 206 × 220 | **1.000** | 9.00 px | 5.15 |
| 1 node, no remembered | 40 | 0 | 83 / 83 | 206 × 220 | **1.000** | 9.00 px | 5.15 |
| 1 node, remembered present | 40 | 44.46 | 38.54 / 38.54 | 206 × 220 | **1.000** | 9.00 px | 5.15 |
| adjacent labelled pair (pitch 48) | 144 | 44.46 | 0 / 0 | 232.91 × 246.91 | 0.885 | 7.96 px | 4.85 |
| 2 × 64 tall lattice | 80 | 0 | 63 / **0** | 206 × 2574 | 0.115 | 1.04 px | 5.15 |

The last row is change 05's "height budget spent as an equivalent width bound"
scenario re-derived: `296 × 206 / 2574 = 23.68px` of drawn width (its shipped
figure was `296 × 116 / 2830 = 12.13px`). The rendered node core is
`80 × 23.68 / 206 = 9.2px` either way — padding neither helps nor hurts when the
height binds, which is exactly the property above.

*Alternatives rejected:*

- **Keep the viewBox upscale and simply lower `maxUpscale` to 1.** Equivalent to
  "never upscale", but it leaves the sparse payload drawing a 40px canvas in a
  206px card — the "the map is the smallest thing in the island" defect change 03
  fixed. The margin is what lets both be true at once.
- **Derive the pitch from the fill (`pitch = availableWidth / cols`).** Makes the
  cell size a function of how many nodes happen to be in view, so the *scale of
  the world* changes as the player walks — and it collapses to 39 units on a
  3-column payload with names, below the row floor.
- **Pad with empty canvas and no dot field.** Then the padding is unexplained dead
  space. The field is what makes margin legible as coordinate space, which is why
  D1 and D5 ship together.

### D6 — `maxWidth: 206`, not the draft's 172

Change 03 deferred this. 172 is not a designed bound: it is the draft's own
`viewBox="0 0 180 150"` less the 8-unit safe border its markers respect, so it is
the natural width of one hand-authored SVG. Our canvas extent is derived from the
placement, so the transferable part of `.mini svg { display:block; width:100%;
max-width:172px }` is `width: 100%` — the map claims its card — and the cap has to
be *our* card: 206px inside the island's 210px content box, leaving the canvas's
1px border and rounding slack on each side.

Adopting 172 would leave 34px of the card unpainted at 83.5% scale, re-introducing
at a smaller amplitude the very defect change 03 fixed, and it would shrink the
drawn label to 7.5 CSS px — below the draft's own rendered 7.64 px. 206 also
becomes the field-padding target under D5, so the island has **one** width knob
rather than a cap fighting a target. The number is retired as a candidate.

### D7 — The axis is drawn only where the convention is stated in words

The shipped requirement already names the axis without drawing it: an edge
direction marker "SHALL be positioned deterministically so that markers never
overlap each other or any node marker, label, **or axis**", and change 05's gutter
proof rests on the band lying "outside the canvas rect containing every node
marker, every node label, and the axis". The invariant has been quoting a line
nothing draws. This change makes the reference true; change 05's proof holds
unchanged, because the axis lives inside the canvas rect and the band is outside
it, by construction.

The axis is two `<line>`s in one `<g>`, full-width and full-height through the
current node's drawn position, painted beneath every node marker (it necessarily
passes *through* the current marker — that is what an origin is). The non-overlap
invariant that names the axis governs the **gutter's edge markers**, not the node
markers, and the requirement says so explicitly so no one reads it as forbidding
the axis from crossing the node it is centred on.

Where it renders is a property, not a surface list: **a surface SHALL draw the
axis only where that same surface states the axis convention in words.** Today
that is the island, whose header carries `北↑ 東→` on the lattice variant; the
overlay states no orientation marks, so it draws no axis and asserts none — which
is the same rule §7.1 applies to the graph variant ("a graph asserts no axis").
The property means that if a later change gives the overlay orientation marks, its
axis follows with no spec amendment; and if the island's marks were ever removed,
the axis would have to go with them.

*Alternatives rejected:*

- **Draw the axis on the overlay too, since that is where the map is studied.**
  It would assert an axis on a surface that never names one — precisely the
  mismatch "SHALL omit those marks otherwise rather than assert a direction or an
  axis the presentation does not support" exists to prevent. Adding orientation
  marks to the overlay is chrome this change does not own.
- **Dash the axis to distinguish it from a connector edge.** A dashed stroke
  already means "blocked exit" in the shared edge language. Extent distinguishes
  it instead: an axis spans the whole canvas and passes through the current node,
  an edge is a short segment between two adjacent markers.
- **Draw the axis above the markers.** It would cross the current node's seal and
  read as a strike-through.

### D8 — What is matched from the draft, and what is refused

The draft's `.lay-grid` labels **collide**. `中央山脈` at `font-size="8"` is 32
units wide on a 24-unit node pitch, so horizontally adjacent labels overlap by 8
units, and the draft hides it by staggering `text-anchor` outward — `x="124"
text-anchor="start"` for the node at 114, `x="56" text-anchor="end"` for the node
at 66. The current node's own label at `y="88"` also overlaps its `r=8` marker at
`y="75"` (the circle with its 2px stroke reaches y = 85; the label's box starts at
82). A pixel-faithful copy of the draft would therefore violate the requirement's
non-overlap SHALL twice over, and would fail the browser geometry audit's ≥2-unit
gap on both axes.

So this change matches the draft's **visual character and proportions** — the dot
field and its pitch's meaning, the vignette's shape and role, the axis cross, a
square cell, the label-to-canvas type ratio (4.37% against 4.44%), the label
sitting below its marker, the node core occupying a minority of the canvas
(57% against the draft's 40%, from today's 66%) — and refuses the draft's
**label collisions** and its self-overlapping current-node label. Where the two
conflict, the non-overlap SHALL wins and the density gives way; D4 states the
exact cost of that choice (5.22 cells against the draft's 7.5) rather than hiding
it.

### D9 — What the overlay gets, and why it cannot regress

`MapLattice.vue` is shared, so every island-only behaviour is an opt-in switch and
every shared behaviour is justified as belonging to the drawing rather than to a
surface:

| layer | island | overlay | why |
| --- | --- | --- | --- |
| coordinate dot field | yes | **yes** | The pitch's meaning is a property of the lattice variant, not of a surface, and the overlay is where the player studies the coordinate space. Gated on the variant, not on a prop. |
| knowledge-edge vignette | yes (`fogVignette`) | **no** | One treatment per surface. The overlay already paints the `mapcanvas` radial gradient; a second wash over it would take its corner dots to ≈1.05:1. Its own gradient darkens outward to `--map-canvas-lo`, against which the dot measures **1.48:1** — better than the island's 1.42:1, so the overlay's far field is already both faint and above the floor. |
| axis cross | yes (`showAxis`) | **no** | D7: the overlay states no orientation marks. |
| field padding | yes (`fieldFill`) | **no** | Opt-in, so the overlay's fill behaviour is byte-identical. Turning it on there is a one-line follow-up the requirement's surface-scoped wording already permits. |
| `labelFont` | 9 | **11** (the default) | The proportion is derived from the surface's own canvas width; 9/206 on the island, 11/848 in the overlay. |
| effective pitch | 40 / 48 | **280 × 212** | The labelled term is `(10 + 1) × 11 + 3 = 124`, below both, so `max()` returns the declared pitch unchanged. |
| `maxUpscale` | removed | never passed it | Removal is unobservable there. |

The overlay's file is therefore **not edited at all**, and the four numbers the
brief guards — `colPitch 280`, `rowPitch 212`, `labelMax 10`, `markerScale 4.83`,
`maxWidth 848` — are untouched. Its only observable change is the dot field it
gains, and a Vitest assertion pins the rest of its geometry as unchanged.

*Alternative rejected:* **making the dot field an island-only prop as well.** The
field is the lattice's claim; withholding it from the surface the player studies
would mean the coordinate space is asserted where it is least readable and dropped
where it is most.

### D10 — `local_map.js` is not edited: the field rect goes through the existing contract

`edgeMarkersFor` takes an explicit surface geometry — `{ canvasWidth, canvasHeight,
current, markerHalf, nameWidth, nameHeight }` — and its header states the contract
this change relies on: "The model NEVER assumes a surface's pitch or scale — each
surface passes its own numbers." So the renderer passes the **padded field rect**
as `canvasWidth`/`canvasHeight` and the current node's position **within that
rect** as `current`, and every invariant the model guarantees carries over:

- markers still sit `outset` inside the *outer* rect, so they remain the canvas's
  outermost band and the coordinate margin sits between them and the node core;
- the "canvas-side tip ≥ 1 unit outside the canvas rect" invariant now refers to
  the field rect, which strictly contains the node core — so the guarantee against
  node markers, labels, and the axis is *stronger*, not weaker;
- `gutter = max(gutterMin, per-edge needs)` and `need = ceil((n × slotMin + 2 ×
  inset − edgeLength) / 2)` is non-increasing in `edgeLength`, so a larger rect can
  only shrink the gutter, never grow it — the band can never eat the margin it was
  given.

No model field, branch, or constant changes, so the dependency-free Node gate
keeps its behaviour and change 05's D5 ("`local_map.js` is not edited") stands
unamended. The gate's packing-invariant table gains no row: the only inputs that
move are `canvasWidth`/`canvasHeight`, which it already varies.

*Alternative rejected:* **per-side gutters in the model, so a marker-free side
costs no band.** Real, but change 05 already priced it as worth ~18 units of
*height* the width-bound island does not spend, and the field padding now absorbs
the same asymmetry for free.

### D11 — This change is coupled to a flagged-optional sibling requirement, and here is the fallback

D4's field regime exists because
`local-map-remembered-are-map-gateways` adds "The map surfaces state a place name
only where it adds information", whose own text says it "is a reviewable addition
… and may be struck without affecting any other requirement in this change". It
does affect this one. Stated plainly:

- **If it stands** (the expected case): a uniform-region wilderness payload draws
  one label, no adjacent drawn-label pair exists, the pitch is 40, and the island
  renders 5.22 cells across with an 8.87px label.
- **If it is struck**: every in-view cell draws a label, an adjacent drawn-label
  pair is the norm on any payload with two horizontally adjacent nodes, and the
  `max()` in D4 returns 48 for essentially every payload. The island then renders
  **4.85 cells across with a 7.96px label** — still better than today's 4.53, and
  every other part of this change is unaffected: the dot field, the vignette, the
  axis, the square cell, the retired upscale, the 9-unit label, the ≤1 scale, and
  the field padding all land regardless, and the sparse payload's 22px label is
  fixed either way.

Nothing in this change's spec text names the sibling requirement or depends on it
textually — the pitch is specified as a derivation over *the drawn label set*,
which is well defined whether or not anything suppresses labels. So a strike costs
density, not coherence, and needs no amendment here.

## Risks / Trade-offs

- **The pitch has two values, so the lattice's density changes when the player
  crosses into a payload with two adjacent named cells** → It is exactly two
  square values (40 and 48, a 20% step), both proven against the same invariant,
  and the switch can only happen on a payload replacement, which already re-draws
  the whole map. The alternative — one always-48 pitch — is the documented
  fallback (D4, D11) if the step reads badly in review.
- **The draft's 7.5 cells across is not reached (5.22 delivered)** → Priced with
  the arithmetic in D4 and D8, including the two levers that would close it and
  why neither is taken here. The visible change the owner asked about is larger
  than the ratio suggests: the canvas goes from **0 drawn dots to ~29**.
- **The dot field could be read as a fifth node state** → Four independent
  guards, each testable: the dot's radius is 1.15 against the smallest node
  marker's 5.5 (3.8× smaller in radius, 14× in area), it carries no stroke, no
  label, no `data-node`, and no activation; it is painted beneath every marker so
  an occupied cell never shows both; it is outside the accessibility tree; and the
  legend gains no entry for it, so
  `webclient-map-scale-legend`'s beyond-state rule keeps the legend's four states
  closed exactly as it does for the wilderness scale note.
- **A decoration layer could be swept into the browser geometry audit** → The
  audit pairs every `.local-map__marker` box and every `.local-map__node-label`
  box. The dot rect, the vignette rect, and the axis group carry neither class —
  the same discipline change 05's edge-marker layer and the landmark ring already
  document in comments — and a Vitest assertion pins the class sets.
- **The vignette departs from the draft's 0.72 outer stop** → Measured and argued
  in D3: at 0.72 the layer erases the far-field dots that are the point. The
  requirement pins the *property* (the vignette never pushes the field below the
  floor), so the specific opacity can be retuned without a spec change.
- **The axis, at 1.39:1, is still a quiet line** → Deliberate: the ceiling is the
  connector edge's own 1.53:1, because an axis that out-reads the topology would be
  a worse drawing. The floor is what a regression test asserts; §7.4's demand is
  met by a number rather than by prose.
- **Lowering the label baseline from 26 to 22 tightens the vertical invariant** →
  The clearances are re-derived in D4 against the widest drawn footprint (the
  actionable halo at 11, not the `local-map__marker` circle at 9) and both land at
  ≥2 units: 2.45 to its own node, 2.95 to the next row's. The audit checks the same
  boxes in viewBox units, so the margin is not scale-dependent.
- **Shrinking the pitch from 58 to 40 shortens the visible connector segment** →
  `40 − 26 = 14` units remain, and the audit's own edge-visibility check (centre
  distance minus the two 13-unit footprints, required strictly positive) passes
  with 14 units where today it passes with 32.
- **A square 40-unit cell makes the island's cell shape differ from the overlay's
  1.32:1** → Accepted, and it is a divergence toward correctness: the island's
  lattice and its edge-direction rays now agree on 45°, where the overlay's still
  disagree by 7.8°. Squaring the overlay is a follow-up its own pitch owns.
- **The field padding is new arithmetic in the width bound** → It is a single
  `max()` before the existing bound, it provably cannot lower the scale (D5), and
  the fixed-point property change 03 pins is untouched: the padding is a function
  of the pitch, the gutter, and `maxWidth`, none of which the canvas's rendered
  size participates in.

## Migration Plan

None needed. The project is pre-release with **zero users**: no persisted client
state, no preference, no payload or protocol change, and no server change. The two
components, the stories, the Vitest suites, and the spec deltas land in one
commit; rollback is reverting that commit.

## Open Questions

- Whether the two-value pitch (40 / 48) survives review or the owner prefers the
  single always-48 pitch (D4's rejected alternative, D11's strike fallback). Both
  satisfy the requirement text as written.
- Whether the overlay should later gain the orientation marks that would license
  its axis (D7) and the field padding switch (D9). Both are additive and need no
  amendment to this change's requirement text.
- Whether the actionable halo's `r 10` should shrink, which is the only remaining
  lever on the cell-count proportion that does not remove a spec'd label (D4).
  It is a pointer-target decision, not a lattice decision, so it is left out.
