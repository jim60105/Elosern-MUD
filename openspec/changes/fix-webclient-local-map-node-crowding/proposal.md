## Why

The HUD redesign roadmap's H2 wave (`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`)
marked the minimap island "Done", and the `webclient-local-map` capability spec already requires that
"no two node markers overlap" and that edges render "as connector lines between node centers". Live
verification against the running client (`podman compose` image `elosern-mud:edge`, 1440×900), compared
frame-by-frame against `docs/design/elosern-redesign/index.html`, shows the shipped `LocalMap.vue`
violates both: `web/webclient-app/components/LocalMap.vue:75-78` lays nodes out on a fixed 24px lattice
cell (`CELL = 24`), but the `current` node's marker is a 26×26 rect and the other markers are r=12
circles (24px diameter) — exactly the width of one cell — so adjacent node markers touch or overlap
edge-to-edge with zero visible gap. The connector `<line>` elements (`LocalMap.vue:212-223`) are drawn
between the same node centers, so at this spacing they render entirely underneath the touching markers
and are invisible in practice. The per-node label (`LocalMap.vue:276-278`, drawn at `y="24"` below each
node) lands almost exactly on the node one row below it, so labels overlap both the next row's marker
and its own label text, making room names illegible (verified: "市場在央爾商街", "旅店第…署公會外" render
as garbled overlapping glyphs). This is the concrete cause of the "map impl is ugly" defect flagged
during this review, and it reproduces on every room with more than one adjacent node — not an edge case.

## What Changes

- Widen the lattice's effective cell geometry in `LocalMap.vue` so a node's own marker footprint and its
  label's rendered height both fit inside their cell with a visible margin to the neighboring cell:
  separate the horizontal column pitch from the vertical row pitch (row pitch SHALL exceed column pitch
  by at least the label's line height) rather than reusing one `CELL` constant for both axes and for
  marker sizing.
  - Reduce marker radius relative to the (now-taller) row pitch, or increase the pitch relative to
    the existing marker sizes — either satisfies the spec; the design doc §D9 lattice model line-number
    references above choose the appropriate constants.
- Fix `nodePos`'s row spacing so a label rendered below one node never falls inside the marker or label
  bounding box of the node in the row beneath it, at every populated lattice size up to the model's
  64×64 bound.
- No change to `local_map.js`'s `layoutNodes`/lattice column-row assignment, the OOB `local_map` payload
  contract, or the `explore.move` submission path — this is a rendering-geometry fix in the Vue
  component only.
- **BREAKING**: none. No prop, DOM testid, payload, or protocol contract changes; `.local-map` and every
  `data-testid="local-map__*"` hook stay exactly as-is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: the "browser minimap renders states without relying on color alone" /
  "in-view nodes occupy distinct lattice cells" requirement gains an explicit scenario pinning down what
  "no two node markers overlap" means in practice — that a node's marker and its label must not visually
  intersect the marker or label of any other rendered node, at every populated lattice size — closing the
  gap between the existing prose requirement and a concrete, testable rendering guarantee.

## Impact

- **Code**: `web/webclient-app/components/LocalMap.vue` only (script constants, `nodePos`, and the
  scoped `<style>` block's canvas/marker sizing). `MapOverlay.vue` is a consumer and needs no change of
  its own — it inherits the corrected geometry automatically because it renders the same component
  unmodified.
- **Stories**: `web/webclient-app/stories/World/LocalMap.stories.js` fixtures already cover multi-node
  grid/wilderness/interior layouts (`LOCAL_MAP_SAMPLE`, `LOCAL_MAP_WILDERNESS_SAMPLE`, etc.); no new
  fixtures are required, only visual re-verification against the existing stories.
- **Tests**: a new browser-level geometry assertion (bounding-box non-intersection between every
  rendered `local-map__node` marker+label pair) extending the existing local-map browser test, plus a
  fast component-level check in `web/webclient-app/tests/` if one already covers `LocalMap.vue` (none
  currently does — the codebase's own dependency graph flags this component as untested).
- **No protocol, read-model, or component-inventory changes.** `component-manifest.json` stays as-is; no
  new component is added.
