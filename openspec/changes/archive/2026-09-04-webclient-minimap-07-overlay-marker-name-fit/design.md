# Design — The Overlay's Marker Names Obey the Geometry That Reserves Them

## Context

`MapLattice.vue` is the shared lattice renderer. Both map surfaces mount it: the
minimap island (`LocalMap.vue`) and the full-map overlay (`MapOverlay.vue`).
Edge direction markers — the presentation of a remembered gateway since
`webclient-minimap-05-edge-markers-replace-list` — are placed by the preserved
UMD render model's `edgeMarkersFor`
(`web/static/webclient/js/elosern/local_map.js:423`), which each surface calls
with its OWN drawing geometry. The model never assumes a pitch or a scale; it is
told one.

Two of the numbers a surface passes describe the room its names will need:

- `nameHeight` — the band's depth, used as `namePad` and so as the gutter that
  keeps names off the canvas rect.
- `nameWidth` — an **outward** name box, i.e. how far a name drawn
  perpendicular to its edge may reach across the band.

The island passes `nameWidth: 0, nameHeight: 16`: it draws its names *along* the
band (horizontal on top/bottom, a stacked glyph column on left/right), so it has
no outward box to declare. The overlay passes
`nameWidth: (labelMax + 1) × 11 = 121, nameHeight: 16`: it draws its names
outward from the diamond's tip, so the box is real.

The model spends those numbers:

| quantity | overlay value | role |
| --- | --- | --- |
| `reach` | 61.48 | `√2 × 9 × markerScale` — the rotated diamond's axial reach |
| `namePad` | 123 | `max(nameWidth, nameHeight) + 2` |
| `outset` | 184.48 | `reach + namePad` — the marker's inset from the outer rect |
| `slotMinH` | 123.95 | `max(2·reach + 1, nameWidth + 2)` — the along-edge slot floor |
| `slotMinV` | 139.95 | `2·reach + 1 + nameHeight` |
| `gutterMin` | 246.95 | `2·reach + 1 + namePad` |

`fittedEdgeMarkers` in `MapLattice.vue` then fits the drawn text — but only for
the island, and it does so against **its own second copy of the model's slot
arithmetic**, with the island's numbers baked in as literals:

```js
const namePad = 18;                      // = max(nameWidth, nameHeight) + 2, ONLY at nameWidth 0
const inset = Math.max(19, 2 * reach + namePad + 1);
const slotMinH = 2 * reach + 1;          // = max(2*reach + 1, nameWidth + 2), ONLY at nameWidth 0
const slotMinV = 2 * reach + 1 + 16;     // nameHeight inlined
```

Evaluated at each surface's declared geometry:

| | `namePad` | `inset` | `slotMinH` | `slotMinV` |
| --- | --- | --- | --- | --- |
| island, model | 18 | 44.46 | 26.46 | 42.46 |
| island, renderer copy | 18 | 44.46 | 26.46 | 42.46 |
| overlay, model | 123 | **246.95** | 123.95 | 139.95 |
| overlay, renderer copy | 18 | **141.95** | 123.95 | 139.95 |

The copy is right for the island by coincidence of `nameWidth: 0` and wrong for
the overlay by 105 units of inset. Deleting the early return alone would
therefore fit the overlay's names against spans that do not exist — a larger
`usable = max(outerLength - 2·inset, …)` yields a larger budget, and the change
would ship the same class of defect it exists to remove.

The early return itself:

```js
if (props.overlayChrome) {
  return markers.map((m) => ({ ...m, visibleName: m.name, glyphs: [] }));
}
```

So the overlay draws the untruncated payload label at
`.local-map__edge-marker-name { font-size: 11px }` against a geometry that
reserved room for eleven glyphs. Nothing detects the mismatch: the model cannot
see the string, and the drawn box is measured by no test.

The arithmetic of the overrun, computed over a 3 × 3 lattice at the overlay's
`colPitch 280 / rowPitch 212 / markerScale 4.83 / labelMax 10`:

| markers on one horizontal edge | per-marker span | glyphs that fit | first overrunning length |
| --- | --- | --- | --- |
| 1 | 840.00 | 76 | 77 |
| 3 | 280.00 | 25 | 26 |
| 5 | 168.00 | 15 | 16 |
| 6 | 140.00 | 12 | **13** |
| 7+ | 124.01 | 11 | **12** |

The span converges on `slotMinH`, and `slotMinH` is pinned by `nameWidth + 2`.
Both the along-edge floor and the outward box therefore resolve to the **same
eleven glyphs at the overlay's 11-unit name step**, because `nameWidth` *is*
`(labelMax + 1) × 11`. That is the number this design uses; it invents none.

Current content sits exactly on the line. The presenter composes a remembered
gateway's label as the far-side anchor display name, qualified with the boundary
node's canonical name when two gateways share a far side
(`web/webclient/presentation/local_map.py:518`). The longest authored region name
is 「西部丘陵與谷地」 (7 glyphs) and the shipped gates are 「南門」/「北門」 (2), so
the worst case today is 「西部丘陵與谷地（南門）」 — eleven glyphs, zero headroom.

## Goals / Non-Goals

**Goals:**

- What a surface draws is bounded by what that surface declared, on both
  surfaces, by construction rather than by a branch.
- One number per surface sizes the glyph *and* budgets the fit, so the drawn
  text and the reserved room cannot drift apart the way they did here.
- The full-map surface stays the disclosure path: strictly more of a name reads
  there than on the island, for every payload.
- The island's fitting, geometry and drawn output are provably unchanged.

**Non-Goals:**

- Growing `nameWidth` so any authored label fits untruncated (D2's rejected
  alternative).
- Changing the overlay's pitches, `labelMax`, `markerScale`, width cap, node
  label size, `mapcanvas` framing, pin, dot field, or legend.
- The island's type ladder, its assistive-technology mirror, and the
  coordinate-field layers.
- The payload, the presenter, and both validators. The preserved UMD render
  model gains one additive field (D6) and no behaviour change.

## Decisions

### D1 — One fitting pass for both surfaces, parameterized rather than branched

The `overlayChrome` early return is deleted. `fittedEdgeMarkers` computes spans,
fits, and de-duplicates for every surface that draws names; what differs between
surfaces is the two numbers they already declare — the name type step and the
outward name box.

This is the same move `labelFont` made for node labels and `markerNameFont` made
for the island's marker names: a surface *declares* the sizes it draws, and the
renderer contains no per-surface conditional for them. The condition that
survives is geometric, not identity-based: *is this marker's name drawn outward
across the band, or along it?*

*Alternative rejected:* keep the branch and add a length cap inside it. It leaves
two fitting implementations to keep in sync, which is the shape of the defect
being fixed — the overlay's early return is exactly such a divergence.

### D2 — The budget is the lesser of the along-edge span and the declared outward box

```
budget = min(
  floor(freeSpanAlongEdge / nameStep),
  drawsOutward ? floor(declaredNameWidth / nameStep) : Infinity
)
```

For the overlay `floor(nameWidth / nameStep) = labelMax + 1 = 11`. For the island
`nameWidth` is 0 and its names are drawn along the band, so the second term does
not exist and its budget is unchanged.

Why the second term binds only on the outward orientation: on a horizontal edge
the name is drawn *along* the edge, so the quantity that must fit is the
along-edge span — and the span is the room the model actually allocated for that
marker, with `nameWidth` acting only as a floor beneath it, never a ceiling. On a
vertical edge the overlay draws the name *outward*, perpendicular to the edge, so
the quantity that must fit is the band depth, which is precisely what `nameWidth`
reserved through `namePad → outset → gutter`. Applying `min` of both terms
everywhere is correct and conservative: on the outward orientation the span is
enormous (840 units) and the box binds; on the along orientation the box is at or
below the span's floor and the span binds.

*Alternative rejected:* declare a truthful `nameWidth` per payload — i.e. have
the surface measure its longest label and tell the model to reserve that much.
Names would then never truncate. But one long authored label would inflate
`namePad`, `outset` and the gutter for the whole canvas, shrinking the drawn
lattice for every payload that carries it; the gutter would become a function of
content length rather than of design. The reserved band is a layout constant on
purpose.

*Alternative rejected:* cap by `labelMax + 1` as a literal. It is the same number
today, but writing it as a literal hides that it is derived from the declared box
— and a surface that later declares a different box would silently disagree with
its own geometry again.

### D6 — The model returns each marker's free span; the renderer stops re-deriving it

`edgeMarkersFor` already computes, per side,
`usable = max(edgeLength - 2·inset, n · slotMin)` and places each marker at
`inset + (slot + 0.5) · usable / n`. The per-marker free span `usable / n` is the
exact quantity `fittedEdgeMarkers` needs and currently reconstructs. The model
gains one additive field on each returned marker:

```js
var marker = { id: …, name: …, landmark: …, dx: …, dy: …, octant: …, side: side,
               span: usable / group.length, x: 0, y: 0 };
```

and the renderer deletes its `namePad` / `inset` / `slotMinH` / `slotMinV` /
`spanBySide` block entirely, reading `m.span`.

This is what makes D1 safe. Parameterizing the renderer's copy — passing
`nameWidth` and `nameHeight` into it and re-deriving the four values with the
model's formulas — would also produce correct numbers today, but it keeps a
second implementation of a contract that lives in the model, and the table above
is what a second implementation costs: the copy tracked the model correctly for
the one surface its author had in hand and silently diverged for the other. The
span is placement data; the placement helper owns it.

The addition cannot regress placement: `span` is derived from values already
computed, is never read back by the model, and changes no returned coordinate.
The dependency-free Node gate's packing invariants are unaffected and gain one
assertion that the returned span agrees with the marker centres it placed.

*Alternative rejected:* return the whole `usable` and `n` per side and let the
renderer divide. It exposes the model's internals rather than the answer, and the
renderer would have to re-group markers by side to use them.

*Alternative rejected:* leave `local_map.js` untouched, as the previous four
changes in this series did, and parameterize the renderer's copy. That constraint
was theirs and was right for them — none of them needed a value the model had
already computed. Honouring it here would mean writing the model's formulas a
second time on purpose, immediately after discovering that doing so is how this
defect was introduced.

### D3 — The overlay declares its name step; the CSS stops hardcoding it

`MapOverlay.vue` gains `:marker-name-font="11"`, and the overlay's `<text>` binds
`font-size` inline the way the island's already does. `11` is what
`.local-map__edge-marker-name` hardcodes today, so **no drawn glyph changes
size**; the hardcoded declaration is removed from that rule, which keeps the
shared font token and colour tier.

The point is not the number but its singularity: the budget divides by the same
value that sizes the glyph. A CSS-only size is invisible to the script that
budgets the fit, which is how a 13px island name came to be budgeted at 13 while
change 06 drew it at ~13 CSS px — the sibling defect this same mechanism already
fixed on the island.

**The declared step must also feed `nameWidth`.** `layoutGeometry` computes
`nameWidth = props.overlayChrome ? (props.labelMax + 1) * 11 : 0`
(`MapLattice.vue:246`), where that `11` is a bare literal — a *third* independent
copy of the overlay's glyph step, agreeing with the CSS rule and with
`MapOverlay.vue`'s declared prop only by coincidence. Declaring the prop while
leaving that literal in place would satisfy the letter of "one number" and miss
its point: a later change to the overlay's declared step would move the drawn
glyph and the fit budget while the placement helper kept reserving room for
11-unit glyphs, reintroducing exactly this defect somewhere new. So `nameWidth`
becomes `(props.labelMax + 1) * props.markerNameFont`. With the overlay declaring
`11` the value is unchanged at 121, so no reserved geometry moves.

*Alternative rejected:* read the computed style at render time. It does not exist
under jsdom (the component suite applies no scoped CSS), it costs a layout read
per marker, and it makes the geometry depend on the document rather than on the
props.

### D4 — Anti-ambiguity now runs on the overlay too, and provably never fires for presenter-authored labels

Truncation makes collisions reachable, so the existing invariant — never draw two
equal names while the payload labels differ — must run on the overlay as well.
The requirement already states it surface-generically; only the implementation
was island-only.

It cannot fire for anything the presenter can author, and the head-and-tail
allocation is why. `fitMarkerName` allocates the **tail first**:

- Parenthesised branch (budget 11, a 4-glyph qualifier such as `（南門）`):
  6 head glyphs + `…` + the whole qualifier. Two names collide only if they share
  their first six glyphs **and** their qualifier. But the presenter appends a
  qualifier only to disambiguate two gateways onto the same far side, and the
  qualifier it appends is the *distinct* boundary node's canonical name — so an
  equal qualifier means the same boundary, i.e. the same node.
- Generic branch (budget 11, a 13-glyph label): 1 head glyph + `…` + 9 tail
  glyphs. Two names collide only if they differ solely within glyphs 2–4 of 13.

The parenthesised branch is therefore closed by the presenter's own
disambiguation rule. The generic branch is **not** proved closed: it merely
requires two labels differing only within glyphs 2-4 of thirteen, and nothing in
the lore registries forbids authoring such a pair. The claim this design makes is
the narrower one — a collision is unreachable through the qualifier mechanism
that exists to distinguish gateways, and merely improbable otherwise. The guard
is therefore live code, not dead code, and task 3.4 tests it directly rather than
treating it as unreachable.

Where the guard does not fire, the overlay's budget produces a name *truncated
with an overflow indicator*, not a dropped one.

*Alternative rejected:* skip the de-duplication on the overlay because it "cannot
happen". Then the one surface that can now truncate is the one surface with no
guard, and the guard is six lines that already exist.

### D5 — The escalation from island to overlay is required to be monotone

The spec gains the clause that the overlay's capacity SHALL be strictly larger,
on the same payload, than the island's. That is what design D8 of change 05
actually meant by calling the overlay the disclosure path, stated as a checkable
property instead of as an unbounded "draws the whole name".

It holds by construction and by a wide margin: on the reported wilderness payload
the island's per-marker budget is 5–6 glyphs at its 10-unit step, the overlay's is
11. It is worth stating because the naive reading of this change — "the overlay
truncates now" — would otherwise look like it weakens D8, and a future change
lowering `labelMax` or raising the overlay's name step could genuinely break it.

## Risks / Trade-offs

- **ACCEPTED REGRESSION — the sighted, keyboard-only, no-AT reader loses the
  unconditional full-name guarantee on the overlay.** The shipped scenario "A
  name the island cannot show is still reachable without assistive technology"
  promised the overlay renders every gateway's name as visible text "where the
  island's span constraints do not apply". That promise was unconditional only
  because the overlay never fitted at all; after this change a label longer than
  the overlay's declared capacity is truncated, and that reader — served by
  neither the visually-hidden mirror nor a hover tooltip, since the marker layer
  is `pointer-events: none` — has no path to the remaining glyphs.

  This design accepts the regression, on the ground that the promise was **not
  actually deliverable in the case it now fails**: a name longer than its
  reserved box does not render "whole and readable", it renders *past the box*,
  overprinting either its neighbouring marker's name or — on a left/right edge,
  where the box IS the band depth — the canvas rect, the node markers, the node
  labels and the axis that the same requirement forbids it to intersect. The
  choice is between a bounded name with an overflow indicator and an unbounded
  name that destroys the drawing it annotates; it is not between truncated and
  whole. The delta spec states this outright as its own scenario rather than
  leaving it implicit, and the untruncated label remains the marker's accessible
  name.

  It is prospective, not current: today's longest authored label is exactly
  eleven glyphs, exactly the capacity. **If the guarantee must be restored
  absolutely**, the route is the Open Question below — give the overlay's
  left/right names the island's along-band stacked-glyph-column placement, which
  replaces the outward box with the (very large) along-edge span as their only
  bound. That is a visual redesign of the overlay and is deliberately not
  attempted here.
- **The model is edited, and every previous change in this series pinned it as
  untouched** → The edit is additive and placement-preserving: one field derived
  from values the function already holds, never read back, changing no returned
  coordinate. The alternative — a second copy of the model's formulas in the
  renderer — is the mechanism that produced this defect, documented in D6's
  table. The Node gate proves the span agrees with the placement at both surface
  geometries.
- **The change touches the shared renderer, so an island regression is possible**
  → The island declares `nameWidth: 0`, so the new term is structurally
  unreachable for it; the spec pins that as its own scenario and the component
  suite asserts the island's drawn names and geometry byte-for-byte against the
  pre-change fixtures.
- **`MapOverlay.vue` is edited, which the previous two changes in this series
  deliberately avoided** → Their constraint was theirs: change 06 avoided it to
  prove its geometry untouched. Here the edit is one declared prop whose value
  equals the CSS constant it replaces, and the change asserts the overlay's
  emitted geometry against the shipped baseline attribute-by-attribute.
- **Deleting the early return changes the overlay's code path for every payload,
  not only crowded ones** → The fitting pass is a pure function over the marker
  set; for a name inside its budget it returns the name unchanged. The suite pins
  that a payload whose names all fit renders byte-identical output to today.

## Migration Plan

None needed. The project is pre-release with **zero users**: no
backward-compatibility surface, no persisted client state, and no payload or
protocol change. The renderer edit, the overlay's declared prop, the spec delta
and the tests land in one commit; rollback is reverting that commit.

## Open Questions

- Whether the left/right overlay names should eventually adopt the island's
  stacked-glyph-column placement, which would replace the outward box with band
  depth and remove the second budget term entirely. Out of scope here — it is a
  visual redesign of the overlay, not a correctness fix — but it is the direction
  that would unify the two surfaces completely.
