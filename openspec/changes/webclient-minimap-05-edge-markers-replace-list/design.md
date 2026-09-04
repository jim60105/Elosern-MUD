# Design — Named Edge Markers Replace the Remembered List

## Context

The minimap island (`web/webclient-app/components/LocalMap.vue`) sits in the stage's
`[data-anchor="hud-right"]` column: 230px wide, a **210px content box** inside the island's
9px padding and 1px border. Its canvas is drawn by the shared renderer `MapLattice.vue`,
which both the island and `MapOverlay.vue` mount.

Three sibling changes are this change's baseline, and its delta text builds on theirs:

- `webclient-minimap-03-canvas-scale-and-budget` — the canvas claims the island's content
  width, every cap resolves into one floored width bound
  `min(maxWidth, maxHeight × canvasWidth / canvasHeight, canvasWidth × maxUpscale)`
  (island: `maxWidth 206`, `maxUpscale 2`), and the height budget is a fixed point measured
  from geometry the canvas does not move.
- `webclient-minimap-04-island-single-affordance` — the island's only affordance is a
  full-bleed transparent `<button>` at `z-index: 0` beneath the content, the header carries
  no control, and the detail line became a **coordinate-only readout** that renders nothing
  (and paints no box, reserving no height) when it has no figure to state — which is exactly
  the coordinate-free case.
- `local-map-remembered-are-map-gateways` — on `grid`/`wilderness`, `remembered` now means
  *a map boundary the player has stood on*, labelled with the authored name of the place its
  traversal reaches, **pairwise distinct within a payload** (the two gates onto one region
  are qualified, e.g. 「西部丘陵與谷地（南門）」), capped at 16, `landmark: true`. On
  `interior`/`instance` it explicitly **keeps** the old meaning ("Coordinate-free layers keep
  the previously-entered meaning … exactly as before").

The defect: `ul.local-map__remembered` renders one chip per remembered node, each with the
same 「◆」 diamond, and the reported wilderness payload produced seven chips all reading
「西部丘陵與谷地」. The owner ruled the list out and asked for a small marker at the map's
edge with its name beside it.

The mechanism exists. `edgeMarkersFor` (`web/static/webclient/js/elosern/local_map.js:423`)
already places a memory diamond on the canvas border where the ray from the current node
through the **raw** payload delta leaves the rect, with a closed-form packing policy:

```
reach    = sqrt(2) * markerHalf              // the rotate(45) diamond's L1 radius
namePad  = max(nameWidth, nameHeight) + 2    // 0 when no names
gutter  >= 2*reach + 1 + namePad
outset   = reach + namePad                   // marker centre inset from the outer rect
inset    = max(19, outset + reach + 1)       // corner clearance
slotMinH = max(2*reach + 1, nameWidth + 2)   // along a horizontal edge
slotMinV = 2*reach + 1 + nameHeight          // along a vertical edge
need     = ceil((n*slotMin + 2*inset - edgeLength) / 2)   // per edge
```

`MapLattice.vue` calls it with `markerHalf = 9 * markerScale` and, today,
`nameWidth = overlayChrome ? (labelMax + 1) * 11 : 0`, `nameHeight = overlayChrome ? 16 : 0`
— so the island passes `0`/`0`, renders the marker layer `aria-hidden="true"`, and draws no
`<text>`. The gating clause is the shipped requirement itself: the markers "SHALL NOT
replace the remembered list, which remains the complete focusable reading path".

The redesign draft is on the owner's side here: `docs/design/elosern-redesign/index.html`
already draws **named** edge markers inside the `.mini` island's `viewBox="0 0 180 150"`
(「東部大平…」 and 「西南海岸」 at `font-size="8"`). Only `REDESIGN.md` §7.2's "Accessibility
floor" bullet — "the existing island remembered-list remains the complete, focusable reading
path … the markers duplicate it visually" — states the contract this change inverts. That
bullet predates the owner's instruction; the instruction wins, and this design supplies the
replacement floor rather than deleting one.

## Goals / Non-Goals

**Goals:**

- On the lattice variant, a remembered gateway is presented exactly once: a diamond on the
  canvas border at its true bearing, with its name beside it.
- No reader loses access. A screen-reader user reaches every remembered place, with its
  **full untruncated** name and its direction in words.
- No drawn name is ambiguous. Two markers whose payload labels differ never render the same
  string — the exact defect this series exists to fix.
- The names are affordable: the island's drawn lattice stays materially larger than the
  ~112 CSS px the owner screenshotted, and marker names render at the island's own type step.
- Interior/instance payloads keep a presentation for their remembered nodes.
- The island's height budget stays a fixed point and the anchor never reaches its
  `overflow-y` fallback.

**Non-Goals:**

- What counts as `remembered` — `local-map-remembered-are-map-gateways`.
- The island's affordance and its coordinate readout — `webclient-minimap-04-island-single-affordance`.
- The draft's dot field, fog vignette, axis cross, and the pitch/font ratios —
  `webclient-minimap-06-draft-lattice-fidelity`.
- The full-map overlay's own marker names, which stay exactly as they ship (D3).
- Any change to the payload, the presenter, the shared validators, or the preserved UMD
  render model (D5).

## Decisions

### D1 — The accessible reading path is a visually-hidden text mirror, not focusable markers

Deleting the list removes the path `:161` names ("SHALL allow focusing a remembered remote
node to view its name/landmark without any travel action") and `:177` guarantees ("the
complete focusable reading path"). The replacement is a **visually-hidden, non-focusable
list** rendered as a sibling of the canvas, generated from the *same* `edgeMarkers.markers`
array the SVG draws, one entry per drawn marker:

```
<ul class="visually-hidden" aria-label="已知的地圖出入口">
  <li>聖潔王都，東北</li>
  <li>西部丘陵與谷地（南門），東</li>
</ul>
```

The name in the mirror is the payload label **untruncated**; the direction word is the
existing `remoteDirection` octant (0..7 → 北/東北/東/東南/南/西南/西/西北). The SVG marker
layer stays `aria-hidden="true"` on the island, so nothing is announced twice. The entries
are ordered by octant then payload index, so the announcement order is deterministic and
matches a clockwise-from-north reading of the drawing.

What a screen reader announces: the island's canvas is a single `role="img"` labelled
「區域地圖縮圖」 (unchanged), followed by a list of *n* items 「聖潔王都，東北」…. What keyboard
order results: **unchanged from change 04** — the island has exactly one tab stop, the
full-bleed affordance. Today's `tabindex="0"` list items disappear with the list and nothing
takes their place in the tab order.

Change 04's full-bleed button contract still holds, and is *strengthened*: 04 put the button
first in DOM order at `z-index: 0` with an empty body, precisely so it can never contain a
focusable descendant. Every element introduced here — the marker `<g>`s and the hidden `<ul>`
— is a **sibling** of that button, and none is focusable, so the button contains no focusable
descendant and the island root still needs no role and no tab stop. 04's `onIslandClick`
guard (`button, a, [tabindex], [data-node]`) is likewise unaffected: the marker layer keeps
`pointer-events: none`, so a pointer click over a marker falls through to the island body and
opens the full map exactly once, as it does today over any decorative layer.

*Alternatives rejected:*

- **Focusable SVG groups (`tabindex="0"` + `role="img"` + `aria-label`), stops but not
  buttons.** This is the closest literal replacement for the deleted list and it was the
  first candidate. Rejected on three counts. (a) It adds up to 16 tab stops to the HUD that
  do nothing when activated — the markers "SHALL carry no activation of its own" — so a
  keyboard user pays 16 presses to cross the island and is rewarded with nothing; the deleted
  list had the same flaw and it is not worth preserving. (b) It puts a visible focus ring on
  a 25 CSS px decoration in the island's gutter band, which is where the design has the least
  room. (c) `tabindex` on SVG child elements is the least portable corner of the platform;
  the mirror is plain HTML and needs no such bet. The one thing focusable groups buy —
  sighted keyboard users learning the untruncated name — is bought instead by the full-map
  overlay, which costs no tab stop on the island (D8).
- **Keeping the list purely for assistive technology (`aria-hidden="false"` but
  `display: none`).** `display: none` removes content from the accessibility tree; it would
  be a path to nowhere.
- **Keeping the visible list on the lattice variant.** The owner ruled it out in the words
  quoted in the proposal. It is kept only where it is not the defect — D4.

### D2 — Names run *along* the gutter band, and the island reserves band depth only

This is the decision the numbers force. The island's content box is 210px and the renderer's
width cap is 206px, so every user unit the model adds to the canvas is paid for by scaling
the whole drawing down. Three candidate geometries, all on the reported wilderness shape
(3 columns × 3 rows ⇒ core `3 × 58 = 174` by `3 × 44 + 14 = 146` user units,
`markerHalf = 9`, `reach = 12.73`):

| island geometry | `namePad` | `gutter` | outer canvas | width bound | scale | **drawn lattice** | name glyph |
|---|---|---|---|---|---|---|---|
| today (`nameWidth 0`, `nameHeight 0`) | 0 | 26.46 | 226.91 × 198.91 | 206 | 0.908 | **158 px** | — |
| **chosen** (`nameWidth 0`, `nameHeight 16`) | 18 | 44.46 | 262.91 × 234.91 | 206 | 0.784 | **136 px** | 13 u → **10.2 px** |
| the overlay's box (`nameWidth (4+1)×11 = 55`, `nameHeight 16`) | 57 | 83.46 | 340.91 × 312.91 | 206 | 0.604 | **105 px** | 11 u → **6.6 px** |

The third row is the decisive one: copying the overlay's outward name box onto the island
would draw the map at **105 CSS px — smaller than the ~112 px the owner screenshotted as
broken** — with 6.6px glyphs beside it. And it is not a tuning problem. Solving
`rendered name = R` for the outward-box family gives
`drawn lattice = 0.7536 × (206 − 2R)`: a 3-glyph name at 10px (R = 30) costs the map down to
132px, a 4-glyph name (R = 40) down to 95px, and the rendered name width can never exceed
206/2 = 103px however much of the map is sacrificed. **An outward, perpendicular name box is
unaffordable at island scale, at every setting.**

The chosen geometry follows from *where* the name is drawn. `namePad` is the reservation
*outward from the marker, perpendicular to the edge*; `nameWidth` additionally widens the
*along-edge* slot. If the name is drawn **along the band** instead of outward from it, its
long axis costs nothing perpendicular:

- **Top/bottom edges** — the name is a horizontal line centred on the diamond and set outward
  of it. Perpendicular extent = one line box; along-edge extent = the name run. This is
  already what `markerNameY()` does today (`-(outset + ascent)` / `+(outset + ascent)`).
- **Left/right edges** — the name is a **stacked glyph column** (one `<tspan>` per code point,
  `dy` = the line step): 直書, upright glyphs, the standard vertical setting for zh-TW.
  Perpendicular extent = one glyph width; along-edge extent = the name run. This replaces
  today's outward-horizontal placement (`markerNameX() = ±markerOutset()`), which is the
  placement that costs 55 units of canvas width.

Passing `nameWidth: 0, nameHeight: 16` expresses exactly that in the *existing* model
contract: `namePad = max(0, 16) + 2 = 18` reserves the band depth, and `slotMinH` falls back
to `2·reach + 1 = 26.46` because the model is told nothing about the along-edge run. The
band arithmetic checks out: `outset = 12.73 + 18 = 30.73`, so the diamond's outward tip sits
18 units inside the outer rect, leaving exactly `namePad` for the name line, and its
canvas-side tip sits `44.46 − 43.46 = 1.0` unit outside the core rect — the model's
"tip ≥ 1 unit outside the canvas rect" invariant, unchanged. Rendered, the band is 34.8 CSS
px deep, of which 14.1 px is the name line: a **13 user-unit** marker-name font renders at
10.2 CSS px, the island's own smallest legible step, in a 16-unit line box.

A consequence worth naming, because it is the collision guarantee: **every marker name is
drawn wholly inside the gutter band, and the gutter band is by construction outside the
canvas rect that contains every node marker, every node label, and the axis.** So a marker
name can never collide with a node label or with the axis cross that
`webclient-minimap-06-draft-lattice-fidelity` will draw. The only collision left to design
against is name-against-name on the same edge — D3.

*Alternatives rejected:*

- **Draw the names in a non-scaling HTML layer overlaid on the canvas.** It escapes the
  viewBox scale entirely (names at a true 10px however small the map gets), but it must then
  be positioned in CSS pixels from the marker's post-scale position, and it still has nowhere
  to put a left/right name: a 210px box minus a 206px canvas leaves 4px of island for a name
  band. It also splits one drawing across two coordinate systems and two collision models.
- **Shrink the island's `maxWidth` to buy an HTML name band.** Same wall: the band needed for
  a 7-glyph name is ~70px per side, leaving ~70px of map.
- **Widen the `hud-right` anchor beyond 230px.** Not this change's surface, and it does not
  help enough: the outward-box family would need 206 + 2 × 90 ≈ 386px of column.
- **Rotate left/right names 90° as a single `<text transform="rotate(-90)">`.** One element
  instead of *n* `<tspan>`s, but CJK glyphs then lie on their side, which is not how zh-TW is
  set vertically. The stacked column keeps them upright.
- **`writing-mode: vertical-rl` on the SVG `<text>`.** The typographically correct answer, but
  its SVG support is the newest and least uniform part of the platform, and its measured
  extent is not something the fit-to-span arithmetic in D3 can compute in advance. The
  stacked column gives an exactly predictable `k × lineStep` extent.

### D3 — Names are fitted to their own free span, and are dropped before they become ambiguous

`labelMax` (island default **4**) governs *node* labels and is not the marker-name budget —
this is important, because 4 is exactly the wrong number here. With
`local-map-remembered-are-map-gateways` the two city gates onto one region are labelled
「西部丘陵與谷地（南門）」 and 「西部丘陵與谷地（北門）」: they differ only at glyph 9. **Any
head truncation shorter than 10 glyphs renders both as 「西部丘陵…」** — seven identical chips
replaced by two identical markers, the same defect in a new shape. The wilderness layer is
kinder (the label is the anchor display name, 「聖潔王都」 = 4 glyphs) but the grid layer is not.

So the island computes a per-marker budget from the geometry it actually has, and truncates
with a **head-and-tail ellipsis that allocates the tail first**. The free span for a marker
is the distance along its edge to the neighbouring marker's slot centre, or to the band's end
where it has no neighbour — both readable from `edgeMarkersFor`'s own return value, which
slots markers uniformly at `centre = inset + (slot + 0.5) × usable / n`. On the chosen
geometry (`inset = 44.46`, outer 262.91 × 234.91):

| markers on that edge | span per marker (top/bottom) | glyph budget at 13 u | span (left/right) | glyph budget |
|---|---|---|---|---|
| 1 | 174 u | 13 | 146 u | 11 |
| 2 | 87 u | 6 | 73 u | 5 |
| 3 | 58 u | 4 | 48.7 u | 3 |
| 4 | 43.5 u | 3 | (gutter grows to 57) | 3 |

A lone gateway on an edge — the overwhelmingly common case, since the presenter caps
`remembered` at 16 and a player near the capital knows two or three — carries its **whole
name**: 「西部丘陵與谷地（南門）」 is 12 glyphs and fits in 13. Two on an edge get 6, which the
tail-first rule spends as 「西…（南門）」; three get 4, which cannot carry a 4-glyph tail plus
an ellipsis, and the visible name is **dropped** — the diamond keeps its position and its
bearing, and the mirror keeps the full name.

That last behaviour is the requirement, stated as a property rather than as the algorithm:
**the island SHALL NOT draw two equal marker names while their payload labels differ.**
Drawing 「西部丘陵…」 twice is worse than drawing one name and one anonymous diamond, because
the first actively asserts that two different places are the same place. The algorithm above
is one way to satisfy it; the invariant is what the spec pins and what the tests check.

*Alternatives rejected:*

- **Reuse `labelMax` (4) for marker names.** Reproduces the defect on the grid layer, as
  shown. It is also the wrong axis: `labelMax` exists to keep two *adjacent lattice cells*'
  labels apart, and marker names have an entirely different neighbour geometry.
- **A fixed, larger marker-name budget (say 8 glyphs) for every marker.** Simpler, but it
  either overruns the span when three markers share an edge, or wastes 5 glyphs of a lone
  marker's 13. Fit-to-span costs one arithmetic pass over an array the renderer already has.
- **Let the model grow the gutter until every full name fits.** This is what passing a real
  `nameWidth` would do, and it is self-defeating: `slotMinH = nameWidth + 2` with a 12-glyph
  name (156 u) and two markers on one edge yields `need = 116`, an outer canvas of 406 u, a
  scale of 0.507, and an 88px map with 6.6px names. Growing the canvas to fit a name shrinks
  the name.
- **Head-only truncation with a longer budget.** Needs ≥ 10 glyphs to disambiguate the gate
  pair, which only the single-marker-per-edge case affords.

### D4 — The graph variant keeps the list, and the two optional sections are mutually exclusive

Edge direction markers are lattice-only, and necessarily so: a radial graph has no canvas
edge that a bearing could point at, and its node `x`/`y` are renderer-local layout values
that "SHALL NOT be read as direction, distance, or place". Meanwhile
`local-map-remembered-are-map-gateways` deliberately leaves `interior`/`instance` on the old
semantics — its scenario "Coordinate-free layers keep the previously-entered meaning" requires
those rooms to keep being emitted as `remembered` nodes "exactly as before". Delete the list
unconditionally and those nodes have **no presentation at all**.

The island therefore keeps `ul.local-map__remembered`, **scoped to the graph variant**. This
is not a half-measure, it is where the defect is not: the owner's complaint was seven
identical chips under a coordinate map that could have shown a bearing instead. An interior
payload has no bearing to show, and its labels are canonical room names — distinct by
construction, informative individually. The list is the correct presentation there and the
wrong one on the lattice, which is exactly what the delta says.

This lands a pleasing invariant on the island's structure. The graph variant's readout is
empty (a coordinate-free layer has no coordinate figure, and change 04's empty-readout rule
already makes it paint no box and reserve no height); the lattice variant has no list. So
**at most one of {remembered list, readout} is ever laid out**, the island has at most three
laid-out sections (meta row, canvas, and that one), and at most two gaps — see D6.

*Alternatives rejected:*

- **Stop emitting `remembered` nodes on interior/instance payloads.** Directly contradicts
  `local-map-remembered-are-map-gateways`, which archives after this change and would revert
  it. It also throws away real information to tidy a renderer.
- **Place the graph's remembered nodes on an outermost "memory ring" of the radial
  placement.** Semantically defensible (BFS distance ∞), visually the nicest answer, and by
  far the most expensive: it changes `layoutRadial` in the preserved UMD source, the radial
  geometry contract, and the non-overlap proof, for the least-visited layer in the game.
- **Slot the graph's remembered diamonds around the canvas border in payload order.** Cheap,
  but a marker on a border reads as a bearing. Placing one on a surface that "asserts no
  axis" invites precisely the false reading the whole spec is written to prevent.
- **Present interior remembered nodes only in the hidden mirror.** Sighted users lose them
  entirely; an accessibility affordance is not a place to hide a presentation gap.

### D5 — `local_map.js` is not edited

The ESM wrapper's header states that the preserved UMD source and its dependency-free Node
gate "are never edited", and `node --test web/static/webclient/js/tests/*.test.js` (416 tests)
covers it. The brief's candidate reason to edit it was per-side gutters, so a marker set
clustered on one edge would not pay symmetric padding on all four. **It is not needed**, for
two reasons.

First, the island's entire requirement is expressible in the existing geometry contract:
`nameWidth: 0, nameHeight: 16` yields exactly the band depth D2 needs, and the along-edge
fitting D3 needs is computed by the island from the marker positions the model already
returns. No new field, no new branch.

Second, per-side gutters would not have bought what they appear to buy. The binding cap on
the island is `maxWidth = 206`, i.e. the canvas's **width**; a per-side gutter only helps a
side with no markers, and any marker at all to the east or west re-imposes the full width
cost. The symmetric-padding waste that per-side gutters remove is real but is worth ~18 units
of *height* on the chosen geometry — height the width-bound island does not spend.

What the change does require of the Node gate is a **test addition, not a behaviour change**:
`local_map.test.js`'s packing-invariant table (`test("edge marker packing clears every legal
input at both surfaces")`) enumerates surfaces as `{island: nw 0, nh 0}` and
`{overlay: nw 72, nh 16}`; the island row becomes `nw 0, nh 16` and the old row stays for the
no-names path. The three invariants it checks (pairwise L1 disjointness, no L1 tip entering
the canvas rect, marker plus name box inside the outer rect) hold unchanged, because the only
input that moved is `nameHeight`, which the model already handles. The gate stays
dependency-free and Node-only.

The parity contract with the Python validator is untouched by construction: `edgeMarkersFor`
is browser-side **render geometry**, and the Python/JavaScript parity that
`webclient-local-map` pins is over the *payload* — field sets, bounds, and serialized size.
This change moves no payload field, no bound, and no visibility rule, so
`web/webclient/presentation/local_map.py` and both validators are untouched and the parity
tests keep passing without edit.

### D6 — The height budget counts the sections it actually lays out

`measureCanvasBudget()` currently hardcodes the list's contribution:

```
gapCount  = 2 + (remembered.length > 0 ? 1 : 0)
others    = metaHeight + rememberedHeight + detailHeight
available = budget - others - gapCount*8 - 18 - 2 - 4 - 1
```

The fixed chrome (25px = 18px island padding + 2px canvas border + 4px meta margin-bottom +
1px rounding slack) and the budget's source — change 03's
`floor(dockTop − anchorTop − 12)`, measured from geometry the canvas does not move — are both
unchanged. What changes is the section list. Because a `display: none` section is removed from
flex layout and generates no gap, the honest formula is derived from the sections actually
laid out:

```
sections  = [meta, canvas, remembered list (graph variant only, non-empty), readout (non-empty)]
gapCount  = laidOutSections - 1                      // 1 or 2, never 3
others    = metaHeight + rememberedHeight + readoutHeight   // two of the three are 0
```

Worked, on change 03's 1280×720 fixture shape (anchor top 64, dock top 500 ⇒ budget
`floor(500 − 64 − 12) = 424`), with change 04's post-affordance meta row of ~15px (the 24px
icon button is gone) and its ~16px readout:

- **Lattice variant** — sections meta + canvas + readout, 2 gaps:
  `424 − (15 + 16) − 16 − 25 = 352`, clamped to the 296px cap. (Change 03's pre-04 reading of
  the same fixture was `424 − (24 + 18) − 16 − 25 = 341`.)
- **Graph variant, 16 remembered** — sections meta + canvas + list, 2 gaps; the list wraps
  ~2 chips per row over 8 rows ≈ 224px: `424 − (15 + 224) − 16 − 25 = 144`. The island's own
  border-box height then sums to `15 + 144 + 224 + 16 + 18 + 2 + 4 + 1 = 424` — exactly the
  budget, so the anchor does not scroll.
- **Graph variant, no remembered** — sections meta + canvas, 1 gap:
  `424 − 15 − 8 − 25 = 376`, clamped to 296.

The name gutter cannot push the anchor into its `overflow-y` fallback, and the proof is short
enough to state. The gutter adds the same `2 × Δ` to the canvas's natural width and height, so
the aspect ratio `H/W` moves monotonically toward 1. Change 03's bound is
`min(206, maxHeight × W/H, W × 2)`, and the rendered height is `bound × H/W`. If `H ≤ W` the
width term binds and the rendered height is `≤ 206 < 296`; if `H > W` the height term binds
and the rendered height is exactly `maxHeight`. **In both cases the rendered height is ≤ the
budget the island measured**, whatever the gutter does. The measurement also stays a fixed
point: the gutter is a function of the marker count and the declared band, never of the
canvas's rendered size, so no feedback path is introduced.

### D7 — What the marker draws, and what it still must not draw

The marker keeps everything the shipped requirement gives it: the memory diamond with the
gold landmark treatment (every remembered gateway carries `landmark: true`), the true-bearing
position from the raw payload delta, no activation of its own, `pointer-events: none`, and
**no distance figure, no angle, and no coordinate readout**. The name is a place name, not a
measurement, so it does not touch that ban.

One clarification the spec must carry, because it is new text on a surface where every
spatial figure is forbidden: the hidden mirror states a **direction word** — one of the eight
octant names 北/東北/東/東南/南/西南/西/西北 — and that is permitted, while a numeric bearing,
an angle in degrees, a distance, and any coordinate figure beyond change 04's current-node
readout all remain forbidden. The octant is the same value the shipped `remoteDirection`
helper already computes to place the marker; naming it in words asserts nothing the drawing
does not already assert, and it is the only way a non-visual reader gets the bearing at all.

### D8 — The overlay is the disclosure path for a name the island cannot show

D1 removes the last focusable descendant, and D3 will drop a visible marker name rather than
draw two names that read alike on one edge. That leaves one reader unserved on the island
itself: a **sighted keyboard-only user with no assistive technology running**. The
visually-hidden mirror is by construction imperceptible to them, and a hover tooltip is not
available — the marker layer is `pointer-events: none` (D7), so no `title` attribute on it
can ever fire, for a pointer user or anyone else. An earlier revision of this document
claimed the tooltip as the mitigation; that claim was false and has been removed.

The real path already exists and costs nothing to specify: change 04 makes the whole island
one full-bleed button, and activating it opens the full-map overlay, which passes
`:overlay-chrome="true"` (`MapOverlay.vue:72`). Under `overlayChrome` the shared renderer
draws **every** edge marker's name as visible `<text>` and as the marker's accessible name,
at the overlay's own scale (`labelMax: 10`, `markerScale: 4.83`, `colPitch: 280`) — where
neither the fit-to-span truncation nor D3's ambiguity rule has any reason to bite, because
the overlay has the span the island lacks. So the sequence is: Tab to the island, Enter, read
every remembered gateway's name at full size.

This is deliberately a *second surface*, not a second control on the island. The island's job
is the glance; the overlay's job is the study. Two names that cannot be told apart at 40 units
of pitch are exactly the case that should send the reader to the surface built for it, and
routing them there costs the island no tab stop, no chrome, and no gutter depth.

Alternatives rejected: re-enabling `pointer-events` on the marker group and adding a `<title>`
(it buys a hover tooltip for pointer users, who are not the unserved reader, while putting a
decoration layer back into hit-testing and into the browser geometry audit's marker pairing);
and making the ambiguous markers focusable after all (D1's three objections apply unchanged,
and it would reintroduce tab stops for precisely the markers that have the least to say).

## Risks / Trade-offs

- **The drawn lattice loses 22 CSS px (158 → 136) to the name band.** → Deliberate and
  priced in D2: it buys the names the owner asked for, it is still 24px larger than the
  ~112px that was reported as broken, and it is 31px larger than the only alternative
  geometry that also shows names.
- **A crowded edge (3+ markers) drops visible names.** → The diamond and its bearing survive,
  the mirror keeps every full name, and the invariant guarantees the alternative — two
  identical strings — never happens. The presenter's 16-node ceiling and real gateway
  topology make 3-per-edge uncommon.
- **A stacked glyph column reads badly for a Latin name** (one letter per line). → World
  content is authored zh-TW and gateway labels come from the authored anchor/region
  registries. Should a Latin name ever appear, the fit-to-span rule truncates it like any
  other and the mirror carries it in full.
- **A visually-hidden mirror can drift from the drawing.** → It is generated from the same
  `edgeMarkers.markers` array in the same computed property, so drift is structurally
  impossible; a test asserts one mirror entry per drawn marker.
- **Sighted keyboard users no longer have a way to focus a remembered place.** → They never
  gained anything from it but the name, which is now visible on the drawing itself. Where
  the island cannot show it — the fit-to-span rule truncated it, or D3's ambiguity rule
  dropped it because two names on one edge would render alike — the disclosure path is the
  full-map overlay, one keystroke away (D8). In exchange the island's tab cost drops from
  1 + n stops to 1.
- **The graph variant keeps a list the owner asked to remove.** → Scoped and argued in D4;
  called out explicitly so the owner can overrule it. If overruled, the fallback is D4's
  memory-ring alternative, which is a `local_map.js` change and a separate proposal.
- **The Node gate's island surface row changes.** → A test-table addition, not a model
  change (D5); the three packing invariants are unchanged and the gate stays dependency-free.
