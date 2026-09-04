# Minimap Canvas Scale and Height Budget

## Why

The minimap island draws a map that is both too small and shrinking. Two
independent defects produce that:

1. **The island's height budget is a feedback loop, not a measurement.**
   `measureCanvasBudget()` reads `anchor.clientHeight` on
   `[data-anchor="hud-right"]`, but that anchor is an absolutely positioned box
   with `top` and `max-height` and no `height` — while its content fits, the
   anchor's height *is* the island's height, and the island's height is
   dominated by the very canvas the budget caps. Substituting the island's own
   box back into the formula
   (`available = budget − others − gapCount × 8 − 18 − 2 − 4 − 1`) collapses it
   to `available = renderedCanvasHeight − 1`: a strictly decreasing map. Every
   ResizeObserver pass shrinks the canvas by a pixel, which shrinks the anchor,
   which re-fires the observer — the minimap ratchets down onto its 40px floor
   one tick at a time. The rendered canvas the owner screenshotted (~112 × 157
   CSS px inside a 210px content box, 54%) is this loop mid-descent.

2. **The canvas draws at natural pixel size instead of claiming its card.**
   The shipped `.local-map__lattice` rule is `width: auto` plus
   `align-self: center`, so a sparse payload renders a ~112px-wide drawing
   inside the island's 210px content box — the map is the smallest thing in the
   island whose entire reason to exist is the map. The redesign draft says the
   opposite: `.mini svg { display:block; width:100%; max-width:172px;
   height:auto }` (`docs/design/elosern-redesign/index.html`).

The island's header compounds the impression: three text items shared one
`space-between` row inside 210px, and a server-authored title
(`f"{room.key}街道圖"`, e.g. 冒險者公會外街道圖 at ~101px) wrapped the row onto
two lines alongside the ~46px axis marks and the ~71px labelled trigger. The
detail line drew a bordered box even when it resolved to nothing, and its
selection went stale after a move — the store replaces the whole payload, but
`selectedId` was seeded once at setup — so the island frequently showed an
empty bordered widget.

The work is already implemented and green in the working tree; this change is
what makes it spec-legitimate, because the shipped `webclient-local-map`
requirement text still describes the old budget derivation and says nothing
about the canvas claiming its width.

## What Changes

- **BREAKING** (spec text, not behaviour anyone depends on): the canvas's
  height cap is no longer "derived from the hud-right anchor's bounded height
  budget" as a rendered-height reading. The budget becomes a **fixed point** —
  it SHALL be measured only from geometry the canvas does not move (the
  island's top edge to the dock anchor's top edge, less a fixed clearance) and
  SHALL NOT be derived from any quantity the canvas's own rendered size
  participates in. Re-measuring a settled island yields the same cap, so no
  observer loop can ratchet the canvas toward its floor.
- The island's canvas claims the island's **content width** (the draft's
  `.mini svg { width: 100% }`) rather than drawing at the placement's natural
  pixel size, uniformly through the viewBox so every marker, label and gutter
  offset in the crowding fix's geometry contract stays proportional.
- `MapLattice.vue` gains a `maxUpscale` prop (`null` = uncapped, so
  `MapOverlay.vue` is untouched and keeps filling its own body width). The
  island passes `2`, so a one-node payload (natural canvas 58 × 58) cannot
  inflate the designed marker/label ramp ~3.5× into a 57px "you are here" seal
  and 39px labels.
- The renderer folds every cap into a **single `max-width` bound**,
  `min(maxWidth, maxHeight × canvasWidth / canvasHeight, canvasWidth ×
  maxUpscale)`, floored to two decimals. The renderer knows its own aspect
  ratio, so it converts the height budget into the equivalent width bound
  instead of leaving a definite width fighting a `max-height` and relying on
  engine-specific replaced-element constraint resolution (which ranges across
  engines from correct ratio-preserving shrink, to a distorted box, to a
  `preserveAspectRatio` letterbox with chrome painted around a thin drawing).
- The island's header becomes localization-safe: the title is the row's single
  elastic item (`flex: 1 1 auto; min-width: 0`, one line, ellipsis, full string
  kept in the element's `title`), while the axis marks and the trailing control
  are `flex: none`. The island card itself claims its anchor's full column
  width instead of being shrink-to-fit, so the card width is a constant of the
  HUD rather than a function of the payload's title length.
- The detail line stops painting a bordered box when it has nothing to say
  (no box, no reserved height, element still mounted for its committed
  test identifier and the island's body-click target), and the island's
  selection is re-seeded from the payload's `current_node` when a newly
  committed payload names a different one — so the readout describes where the
  player *is* after a move instead of a node the new payload no longer carries.

Out of scope — each is owned by a later change in this series:

- Removing the visible expand button in favour of a full-bleed transparent
  button affordance → `webclient-minimap-04-island-single-affordance`. (The
  same pass that produced this change's baseline also reduced the button's
  visible label to a 24×24 glyph; that reduction is deliberately **not**
  specified here, because change 04 removes the visible control outright.)
- Redefining `remembered` as a map gateway rather than "any previously entered
  node outside the field of view" → `local-map-remembered-are-map-gateways`.
- Deleting the remembered list and moving the place names onto the edge
  markers → `webclient-minimap-05-edge-markers-replace-list`.
- The draft's far-field dot field, fog vignette, axis cross, and the
  pitch/font-ratio question — including whether the width fill should be
  achieved by scaling the viewBox (as here) or by spreading the lattice pitch →
  `webclient-minimap-06-draft-lattice-fidelity`.

Not in scope at all: the `local_map` v1 payload, the server presenter, the
preserved UMD render model (`web/static/webclient/js/elosern/local_map.js`) and
its dependency-free Node gate, tap-to-move, and the overlay's focus-restore
contract. The project is pre-release with zero users, so there is no backward
compatibility surface and no migration path to design — the components, their
Vitest suites and the spec land in one commit.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: "The browser minimap renders states without relying on
  color alone" — the island canvas's sizing clause gains the fill-width rule,
  the bounded uniform upscale, and the single-width-bound cap resolution; the
  height-budget clause gains the fixed-point property that forbids deriving the
  budget from anything the canvas's own size participates in; the island's
  title clause gains the single-row, localization-safe header rule; and the
  detail line gains its follow-the-payload selection and no-box-when-empty
  rules.

## Impact

- Affected code: `web/webclient-app/components/MapLattice.vue` (`maxUpscale`
  prop, `widthCaps()` cap folding, `.local-map__lattice` fill rules),
  `web/webclient-app/components/LocalMap.vue` (`anchorHeightBudget()` and
  `ANCHOR_BOTTOM_CLEARANCE`, `:fill-width` / `:max-upscale` on the lattice, the
  meta-row flex budget and title `title` attribute, the `--empty` detail
  modifier, the `currentNode` watcher and the `activeNode` fallback), and
  `web/webclient-app/stories/World/MapLattice.stories.js` (island-scale stories
  render in a 210px content box with the island's fill props).
- Affected tests: `web/webclient-app/tests/world/local_map.test.js` — the
  fill-width and upscale-bound style assertions, the header-squeeze assertion,
  the readout re-seed / fallback / empty assertions, and the ratchet regression
  test that drives eight measurement passes against a hostile content-sized
  anchor and requires an identical cap on every pass. Browser suites
  `web/tests/browser/test_browser_local_map.py`,
  `test_browser_contextual_hud.py`, `test_browser_layout.py` and
  `test_browser_shell.py` are re-run unchanged as the island-bounds regression
  gate.
- No server, protocol, store, or payload change; the Python/JS validator parity
  contract and the Node gate are untouched.
- The requirement title is MODIFIED in place (no rename), so every existing
  `@covers_requirement` anchor on
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  stays valid.
- No player-facing command changes; `docs/game/commands.md` untouched.
