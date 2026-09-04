# Design — Minimap Canvas Scale and Height Budget

## Context

The minimap island (`web/webclient-app/components/LocalMap.vue`) renders inside
`[data-anchor="hud-right"]`, a `position: absolute` column with `top: 64px`,
`right: 16px`, `width: 230px`, `max-height: calc(100% - var(--dock-h) - 110px)`
and `overflow-y: auto` (`HudFrame.vue:147`). It has **no** `height`, so while
its content fits, the anchor is content-sized: its rendered height *is* the
island's height. The island's own card is `padding: 9px` inside a 1px border,
so its content box is 210px wide in that 230px column.

The canvas is drawn by the shared renderer `MapLattice.vue`, used identically
by the island and by `MapOverlay.vue`. The renderer computes a natural pixel
canvas from the exported placement (lattice: `cols × colPitch + 2 × gutter` by
`rows × rowPitch + 14 + 2 × gutter`) and, before this change, emitted
`max-width: <maxWidth>px` + `max-height: <maxHeight>px` with CSS
`width: auto; align-self: center` — i.e. it drew at natural size and only ever
shrank. `LocalMap.vue` measures a dynamic height budget every ResizeObserver
tick and passes it down as `maxHeight`.

Two facts collide there:

```
budget    = anchor.clientHeight                        // == island height
available = budget − others − gapCount×8 − 18 − 2 − 4 − 1
island    ≈ others + gapCount×8 + 18 + 2 + 4 + canvas  // border-box identity
⇒ available = canvas − 1
```

`available` is then clamped to `[40, 296]`. `available = canvas − 1` is a
strictly decreasing map with a single attractor at the 40px floor: every
observer pass shrinks the canvas by a pixel, the anchor shrinks with it, the
observer re-fires. The ~112 × 157 CSS px canvas the owner screenshotted inside
a 210px content box is that descent, caught mid-way.

The redesign draft (`docs/design/elosern-redesign/index.html:228`) states the
opposite intent for the same card: `.mini svg { display:block; width:100%;
max-width:172px; height:auto }` — the map claims the card.

The working tree already carries the implementation this document describes;
the suites are green (`npx vitest run`: 76 files / 745 tests). This design
records the decisions so the shipped behaviour is spec-legitimate.

## Goals / Non-Goals

**Goals:**

- The island's height budget is a **fixed point**: measuring an already-settled
  island yields the same cap, so no observer-driven loop can walk the canvas
  down.
- The island's canvas claims the island's content width instead of drawing at
  natural pixel size, uniformly, so the crowding fix's marker/label/gutter
  geometry stays proportional and its non-overlap invariant is untouched.
- Every cap the renderer is given resolves to one deterministic bound the
  renderer itself computes, not to an engine-dependent constraint resolution.
- The island's header survives any server-authored title length without
  reflowing, and the readout line never presents an empty bordered widget.
- `MapOverlay.vue` is not touched, and cannot be affected: the new upscale
  bound defaults to `null` (uncapped).

**Non-Goals:**

- The visible expand control's fate (`webclient-minimap-04-island-single-affordance`).
- The meaning of `remembered` (`local-map-remembered-are-map-gateways`) and the
  removal of the remembered list (`webclient-minimap-05-edge-markers-replace-list`).
- The draft's far-field dot field, fog vignette, axis cross, label/pitch font
  ratios, and **how** the fill is achieved geometrically
  (`webclient-minimap-06-draft-lattice-fidelity`) — see D7.
- Any change to the payload, the presenter, the preserved UMD render model, or
  the placement arithmetic in `web/static/webclient/js/elosern/local_map.js`.

## Decisions

### D1 — Measure the budget from geometry the canvas does not move

`anchorHeightBudget(anchor)` reads the vertical distance from the island
anchor's top edge to the dock anchor's top edge, minus a fixed
`ANCHOR_BOTTOM_CLEARANCE = 12`, floored:

```
room = floor(dock.getBoundingClientRect().top
             − anchor.getBoundingClientRect().top
             − 12)
```

Both edges are stage-positioned (`top: 64px` for the anchor; the dock is
`--dock-h`-tall and bottom-anchored), so neither moves when the canvas resizes.
The 12px clearance is what makes the measured budget strictly smaller than the
anchor's own CSS cap (`calc(100% - var(--dock-h) - 110px)` leaves 46px below
the anchor, all of which the 46px command line claims), so the island can never
grow into the anchor's `overflow-y` fallback.

Worked example, the shape the Vitest regression test pins (a 1280×720 stage):
anchor top 64, dock top 500 ⇒ budget = `floor(500 − 64 − 12)` = 424;
`available = 424 − (meta 24 + detail 18) − 2 gaps × 8 − 25 fixed chrome` = 341,
clamped to the 296px cap. The old reading budgeted from ~236px of island and
handed the canvas 177px on the first pass — and less on every pass after it.

The bare-mount fallback (`return anchor.clientHeight`) is kept for component
tests and Storybook, where an authored anchor's height is a fixture, not an
island-fed quantity, and where no dock sibling exists.

*Alternatives rejected:*

- **Keep `clientHeight`, add hysteresis / a minimum delta before re-applying.**
  Damping a feedback loop is not removing it; the fixed point would still be
  wherever the damping stalls, and it would differ per machine and per font.
- **Subtract the island's own rendered height from the anchor first.** Still
  self-referential — the island's height *is* dominated by the canvas.
- **Read the anchor's resolved CSS `max-height`.** It is a stage-relative
  static bound, so it does not ratchet, but it ignores the anchor's `top: 64px`
  offset and over-budgets the island by exactly the clearance the command line
  needs; it also parses a computed style string, which is brittler than reading
  two rectangles.

### D2 — Spec the budget as a property, not as the recipe

The requirement states that the budget SHALL be a fixed point and SHALL NOT be
derived from any quantity the canvas's own rendered size participates in — not
"SHALL be measured from the dock anchor's top edge". The concrete measurement
is recorded here in D1 instead.

*Rationale:* the dock's position is a layout fact that a later HUD change may
legitimately move (change 04 alters the island's own affordance; a dock
redesign would alter the other edge). Freezing the DOM query into the
requirement would force a spec amendment for a layout tweak while protecting
nothing the property does not already protect. The property, by contrast, is
exactly what the bug violated, and is directly testable: drive N measurement
passes against a hostile content-sized anchor and require an identical cap on
every pass.

### D3 — The island fills its content width, bounded by a uniform upscale factor

`LocalMap.vue` passes `:fill-width="true" :max-upscale="2"`. `fillWidth`
(already present for the overlay) sets `width: 100%`; the new `maxUpscale` prop
bounds how far the natural canvas may be *enlarged*. It defaults to `null`
(uncapped), so `MapOverlay.vue` — which passes no upscale bound — keeps filling
its own body width at its own larger scale with no edit at all.

Scaling happens through the viewBox, so it is uniform: every marker radius,
label offset, and edge-marker gutter in the crowding fix's geometry contract
scales together, and the non-overlap invariant (a pre-scale property) is
scale-invariant. At the island's `maxUpscale: 2` the 11px node label tops out
at 22px drawn.

Concrete bounds this produces on the island (natural → drawn):

| payload | natural canvas | bound that binds | drawn width |
| --- | --- | --- | --- |
| typical grid sample | 226.91 × 110.91 | `maxWidth` 206 | 206px |
| single-node room | 58 × 58 | `58 × 2` | 116px |
| 64-row lattice | 116 × 2830 | `296 × 116/2830` | 12.13px |

*Alternatives rejected:*

- **Fill unbounded.** A one-room payload's 58px canvas stretched to the card is
  a ~3.5× blow-up of the designed ramp: a 57px "you are here" seal and 39px
  labels. The bound keeps the drawn ramp near the draft's while every payload
  from two columns (or one column plus the edge-marker gutter) up still claims
  the whole card.
- **Adopt the draft's literal `max-width: 172px`.** 172 is the draft's own
  natural SVG width (`viewBox="0 0 180 150"`), not a designed cap for our
  renderer's canvas; our equivalent is the shipped `maxWidth: 206`, which sits
  just inside the 210px content box. Revisiting it belongs with the rest of the
  draft-fidelity work (change 06).
- **Spread the lattice pitch so the natural canvas already equals the card.**
  See D7 — deferred, deliberately.

### D4 — Fold every cap into one `max-width` bound

`widthCaps()` collects the caps and `latticeStyle` emits
`max-width: floor(min(caps) × 100) / 100 px`:

```
min( maxWidth,
     maxHeight × canvasWidth / canvasHeight,
     canvasWidth × maxUpscale )
```

Under `fillWidth` the element's width is *definite* (100% of the caller's
content box). A definite width plus a bare `max-height` on an SVG is the
replaced-element constraint case whose observable behaviour ranges across
engines from the ratio-preserving shrink the spec table intends, to a distorted
box, to a `preserveAspectRatio` letterbox that leaves the canvas's background
and border painted around a thin drawing. The renderer knows its own canvas
ratio exactly, so it spends the height budget as its *equivalent width*
instead: the drawing then fills its box in every engine, and the rendered
height is exactly the budget. `max-height` is still emitted as the
belt-and-braces cap it always was; it can no longer bind, because the width
bound is floored rather than rounded up (rounding up could re-cross the budget
by a sub-pixel and hand the anchor a scrollbar).

*Alternative rejected:* leave `max-height` as the operative cap and let the
engine resolve the ratio. That is what produced the "which engine are we on"
question in the first place, and it is untestable in jsdom, where the assertion
would have to be about a style string the engine reinterprets anyway.

### D5 — Re-budget the header instead of re-sizing its items

The header is a three-way squeeze inside 210px: a server-authored title
(`f"{room.key}街道圖"`; 冒險者公會外街道圖 ≈ 101px), the ~46px axis marks, and the
~71px labelled trigger — ~218px of content in a 210px row, so all three wrapped.
`justify-content: space-between` cannot help here: with three items that all
want to be wider than the row, "space between" only decides *where* the
wrapping happens. The row becomes `gap: var(--sp-2)` with exactly one elastic
item:

- title: `flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis`, plus a `title` attribute carrying the complete
  string. `min-width: 0` is what actually permits the shrink — a flex item's
  default `min-width: auto` floors it at its own max-content width, which is
  precisely how a 9-glyph title pushed the row into a wrap.
- axis marks and the trailing control: `flex: none`.

`.local-map` also gains `width: 100%`. The anchor is `align-items: flex-end`,
so the island was shrink-to-fit: its card width was decided by whichever row
happened to be widest, meaning a short title made the card — and therefore the
canvas — narrower. A minimap is a fixed station in the HUD, so its card width
is a constant of the layout, not a function of the payload.

This is specified as a **localization-safe container** rule: the payload's
`title` is bounded only by the schema's 128-code-point ceiling, so no authored
or translated length may reflow the header.

*Alternatives rejected:* shrinking the title's font (illegible at 10px and
below, and it only postpones the wrap by a few glyphs); truncating the title
server-side (the server authors identity — the client must be safe for *any*
length it is handed); letting the header wrap to two rows (it spends the canvas
height this change just recovered, on decorative chrome).

The same pass also reduced the trigger's visible label to a 24×24 glyph. That
is deliberately **not** specified here: change 04 removes the visible control
outright, so only "the trailing control is a fixed-size item" is stated — a
claim that stays true whichever control survives.

### D6 — The readout follows the payload, and says nothing rather than framing nothing

Two independent staleness paths produced the empty bordered bar:

1. The store swaps `localMapModel` wholesale on every move, but `selectedId`
   was seeded once at setup, so after one move the held id named the previous
   room — a node the new payload frequently no longer carries. A
   `watch(() => props.localMap.currentNode)` re-seeds `selectedId` and clears
   `hoveredId`, restoring the documented default (the readout describes where
   you are) without disturbing a manual selection made inside one payload.
2. A targeted panel update can drop the selected node while `currentNode` is
   unchanged (same room, different visible neighbours). `activeNode` therefore
   falls back to the payload's current node before resolving to nothing.

When nothing resolves at all (the degenerate branch — every available payload
carries a current node), the line takes a `--empty` modifier that sets
`display: none`: no border, no padding, and `sectionHeight` reads 0 so the
height budget does not reserve a blank line either. The element itself stays
mounted, because `local-map-detail` is a committed test identifier and the line
is part of the island's plain-text body click target.

*Alternative rejected:* `v-if` the element away — it would break the committed
testid and remove a click target for no additional benefit over `display: none`.

### D7 — Honest supersession: this fill is a viewBox scale, and change 06 may replace it

Filling the card by scaling the viewBox is not the only way to honour
`.mini svg { width: 100% }`. The alternative is to **spread the lattice pitch**
so the natural canvas is already the card's width, which is what the draft
actually draws: one dot per coordinate cell at pitch 24 on a 180-unit canvas,
~7.5 cells across, labels at `font-size 8` (4.4% of canvas width). Under a
viewBox upscale the label-to-canvas ratio is preserved rather than corrected,
so a sparse payload gets *large* markers and labels on a large canvas, where
the draft would show the same small type on a wider lattice.

That question — pitch versus scale, the label/pitch font ratio, the far-field
dot field, the fog vignette, and the axis cross — is exactly
`webclient-minimap-06-draft-lattice-fidelity`'s subject, and this change's
`maxUpscale` viewBox approach is **expected to be superseded** there.

Shipping it now is still right:

- It fixes a live, user-visible ratchet bug (D1/D2) that has nothing to do with
  how the fill is achieved, and the budget's fixed-point property survives any
  later geometry change unchanged.
- The **principle** the spec states — the drawn map claims the island's content
  width and is never narrower than its card merely because the payload is
  sparse — is what change 06 would also have to satisfy. Only the mechanism
  changes, and the mechanism is not in the requirement text.
- Pitch spreading touches the crowding fix's non-overlap geometry contract and
  the ≥2px separation guarantee; sequencing it behind the bug fix keeps the two
  risks apart.

## Risks / Trade-offs

- **The `clientHeight` fallback keeps the old self-referential read alive for
  bare mounts** → In that context the anchor is an authored fixture, not
  island-fed, so it cannot ratchet; the Vitest regression test reproduces the
  *shell* shape (a hostile anchor whose `clientHeight` getter reports the
  island's own rendered height) and requires an identical cap across eight
  passes, so a regression to the shell path is caught.
- **`maxUpscale: 2` is a chosen constant** → It is pinned by an assertion
  (a 58px natural canvas caps at 116px), justified against the ~3.5× ramp
  blow-up it prevents, and is one of the numbers change 06 re-derives from the
  draft's pitch/font ratios.
- **Flooring the width bound to two decimals leaves up to 0.01px of budget
  unused** → Deliberate: rounding up could re-cross the height budget by a
  sub-pixel and hand the anchor a scrollbar, which is the failure the budget
  exists to prevent.
- **Upscaling enlarges every stroke and label uniformly** → Bounded at 2× on
  the island (an 11px label draws at most 22px), and the non-overlap invariant
  is a pre-scale property that uniform scaling preserves, so the crowding fix's
  guarantee is untouched.
- **A future header item added to the meta row would re-open the squeeze** →
  The requirement states the rule structurally (exactly one elastic item; every
  other header item fixed-size), so a new item lands on the fixed side by
  construction, and change 04 removes an item rather than adding one.

## Migration Plan

None needed. The project is pre-release with **zero users**, so there is no
backward-compatibility surface, no persisted client state involved (no
preference, no storage write), and no payload or protocol change. Components,
stories, Vitest suites and the spec delta land in one commit; rollback is
reverting that commit.

## Open Questions

- Whether change 06 replaces the viewBox upscale with lattice-pitch spreading
  (expected yes — D7) and whether it re-derives `maxWidth` from the draft's
  172px in the process. Neither answer changes the requirement text this change
  writes.
