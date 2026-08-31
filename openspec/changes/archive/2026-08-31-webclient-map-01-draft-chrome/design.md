# Design: webclient-map-01-draft-chrome

## Context

`MapLattice.vue` is the single shared lattice renderer (node markers, connector
edges, per-node labels, state legend) parameterized by pitch/scale; `LocalMap.vue`
renders the HUD island around it and `MapOverlay.vue` renders the full surface
with a larger pitch (`colPitch 280 / rowPitch 212 / markerScale 4.83`). The
placement model lives in `web/static/webclient/js/elosern/local_map.js`
(`reducePanel`/`layoutNodes` produce the bounded integer lattice). The redesign
draft's map surfaces use a different visual language (seal-red circle current
node, ink dots, gold landmarks, `mapcanvas` dark terrain overlay, dot-chip
legends) but the shipped surfaces still use the pre-redesign amber-square /
monospace chrome.

The roadmap slices the map work into three waves, landed strictly in order:
`webclient-map-00-story-fidelity` (fixtures/stories — the completed prerequisite
this wave builds its visual acceptance surface on), this wave 1 (chrome), and
wave 2 (`webclient-map-02-layout-variants`, the only following map wave) which
adds the draft's connected-node layout as a data-derived (payload-resolved) variant. Wave 1 therefore
re-skins the *existing* lattice placement in draft style and does not touch the
placement model.

## Goals / Non-Goals

**Goals:**

- Pixel-level draft fidelity for everything wave 1 can express on the lattice:
  marker shapes/colours, edge strokes, label tiers, island header, overlay
  `mapcanvas` frame + gradient + teardrop pin, dot-chip legends.
- All behavioural contracts untouched: DOM-independent lattice model,
  non-overlap at every scale, shared parameterized renderer, no
  bearing/compass/distance claims, the labelled expand sibling with focus
  restore, combat hiding via the `local-map` root class.
- The orientation marks follow the draft: the coordinate-layer header pair is
  `北↑ 東→` (the shipped single `北↑` gains `東→`; wave 2 conditions the pair
  further on the lattice variant).
- Draft colours enter `tokens.css`; components never hardcode draft hex.

**Non-Goals:**

- The radial connected-node layout and its data-derived two-variant resolution (wave 2),
  story fixture restructuring (wave 3).
- Compass bearing, zoom/pan affordances, tracked-route line: forbidden by
  `webclient-local-map` / `webclient-contextual-hud` specs and backed by no read
  model. Not implemented, not stubbed.
- Any server, presenter, protocol, or store change.

## Decisions

### D1 — Chrome-only; placement model untouched

Wave 1 restyles the lattice as-is. Alternative considered: jump straight to the
draft radial layout — rejected because it couples re-skin risk to layout risk and
the main spec mandates lattice placement in the model until wave 2's delta lands.
Consequence: the island after wave 1 is "draft-painted grid", fully consistent
with the two-variant plan (the grid variant *is* the wilderness surface).

### D2 — Marker geometry: circles, sizes 8 / 4.5 at island scale

Current node: filled circle `--seal-deep` (#a52c31), stroke `--seal-light`
(#e06b6b) sw2, r8 at island scale (overlay scales via existing `markerScale`).
`visible_visited`: filled circle `--ink-700` (#2c2634) stroke `--ink-edge`
(#3a3344), r4.5. `visible_unvisited`: hollow circle, stroke only (keeps the
`未探索` rule), r4.5 with the gold landmark fill only where the payload marks a
landmark node (`--gold-500`, r5, per draft `.mini` landmark dots). `remembered`
stays out of the canvas in its list; its list marker becomes the rotated-square
(diamond) at draft scale. Shape ladder (big stroked circle / small solid / small
hollow / diamond) keeps states distinguishable without colour. Non-overlap is
preserved because the new footprints are strictly smaller than the current
26 px square / r12 circles, so the existing pitch guarantee remains valid; tests
assert the new footprints.

### D3 — New tokens, names `--seal-deep`, `--seal-light`, `--ink-edge`, label tiers

The draft's exact values lack tokens (`--seal-600` is `#a9322a`, not the draft's
`#a52c31`). Add `--seal-deep: #a52c31`, `--seal-light: #e06b6b`,
`--ink-edge: #3a3344`, and label-tier tokens `--map-label-here: #f2ecdf`,
`--map-label-gold: #e2c06a`, `--map-label-seen: #8d8370`,
`--map-label-far: #615a4c`. Rationale: tokens are the project's single source for
colour; redefining `--seal-600` globally would silently repaint every other
surface. Existing `--gold-500`/`--ink-700` are reused where they already match.

### D4 — Overlay terrain is CSS-only

The `mapcanvas` background is the draft's `radial-gradient(70% 60% at 40% 30%,
#1a1420, #0c0a10)` plus radius-12 `--ink-600` border as plain component CSS; no
SVG terrain paths are drawn. Rationale: terrain paths in the draft are
decorative fiction — drawing node-hull-derived "coastlines" would invent
geography the payload doesn't claim (truthful-rendering rule in
`webclient-component-showcase`). The teardrop pin is a fixed SVG path anchored
directly above the current-node circle — an adornment of the real marker, not a
second position claim.

Ownership: the pin is rendered inside `MapLattice.vue`'s SVG behind an
`overlay-chrome` prop (off on the island), anchored to the CURRENT placement's
current-node coordinates — not positioned by `MapOverlay.vue`'s wrapper, which
would duplicate the coordinate system and strand the pin once wave 2's variant
parameter changes coordinate sourcing. Test obligation: exactly one pin sharing
the current marker's x and vertically above its y.

### D5 — Whole-island click is pointer sugar, not an a11y surface change

The island root gets a `click` handler opening the map overlay unless the event
origin is inside an interactive descendant (`button`, `a`, `[tabindex]`, list
item), guarded with `closest()`. The root does NOT gain `role="button"` or
`tabindex`: the labelled `local-map__expand` sibling remains the sole keyboard
path, preserving the focus-restore contract the browser tests pin. The draft's
`cursor: pointer` is applied to the non-interactive island body.

### D6 — Legends become dot-chips but keep text labels

Draft chips: 11×11 radius-3 square chip + 11px label, 14px gap, no bordered
pill. Non-colour redundancy is carried by the text labels (already required) and
by chip border style for the remembered chip (solid vs dashed per draft
legend). The orientation marks keep the spec's coordinate-layer conditioning:
the island header shows the draft's `北↑ 東→` pair only on coordinate layers
(the shipped single `北↑` mark gains `東→`; the pair is what the draft's map
header draws — see `REDESIGN.md` §7), and wave 2 conditions the pair further on
the lattice variant.


## Risks / Trade-offs

- [Vitest geometry tests pin old marker sizes/attrs] → update
  `world/local_map.test.js`, `world/map_lattice.test.js`,
  `overlays/map_overlay.test.js` in the same commit; selectors/ids unchanged.
- [Island click over-fires when activating remembered list items] → `closest()`
  guard + the list's own handlers stop propagation; Vitest case asserts
  clicking a remembered item does not emit `open-map`.
- [Small r4.5 dots on a 230 px island could crowd labels] → label footprint
  rules unchanged; if a scale needs it, existing scale-down path applies
  uniformly (non-overlap guarantee is scale-invariant).
- [`--seal-deep` close to existing `--seal-600`] → tokens documented as
  draft-map-specific; no global rename, no repaint risk.
