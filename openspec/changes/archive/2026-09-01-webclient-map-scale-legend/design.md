# Design: webclient-map-scale-legend

## Context

`web/webclient/presentation/local_map.py` assembles the payload legend once for every layer as
`list(LEGEND_LABELS)` — the four fixed visibility-state labels — and `MapLattice.vue` renders
each entry with a chip whose style cycles through the four states
(`LEGEND_STATES[index % LEGEND_STATES.length]`). The main spec already allows legend lists up to
16 entries and the shared-renderer requirement says extra entries cycle, so the payload schema,
the Python validator, and the JS validator all tolerate a fifth entry without change. The user
asked specifically: the expanded full-map overlay must show the 10 km/cell wilderness scale.

## Goals / Non-Goals

**Goals**

1. The wilderness-layer payload legend states the cell scale, derived from
   `WILDERNESS_KM_PER_CELL` at build time — a single constant source (AGENTS.md: consumers read
   registry/provider values, never duplicate constants).
2. Non-state legend entries are visually distinct from the four visibility chips so the scale
   line is never misread as a fifth node state (the no-color-alone rule generalizes).
3. The scale reaches exactly the surface the user named: the overlay renders the payload legend;
   the minimap island renders none (existing contract, untouched).

**Non-Goals**

- Any distance/ruler/measurement interaction; any scale statement on grid/instance/interior
  layers (grid cells are not 10 km); any new payload field or validator change.

## Decisions

### D1 — Server-side legend extension, not a new payload field

`local_map.py` keeps `LEGEND_LABELS` for the states and appends one localized scale label when
the built layer is `wilderness`:

```python
from world.maps import wilderness_provider  # module import, NOT from ... import the constant

wilderness_legend = (
    *LEGEND_LABELS,
    f"每格約 {wilderness_provider.WILDERNESS_KM_PER_CELL} 公里",
)
```

The figure is read as a module attribute of `world.maps.wilderness_provider` at
legend-assembly time — the same module the wilderness layer adapter already reads bounds from —
so a future scale change is one constant edit AND the single-constant-following scenario's
`patch("world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL", …)` actually changes what the
presenter reads. A `from … import WILDERNESS_KM_PER_CELL` binding would freeze the value at
import time and make that test provably impossible to satisfy — rejected. Adding a
`scale_km_per_cell` payload field instead was also rejected:
it widens the exact schema both validators pin, requires JS-validator churn for one text line,
and the legend already is the spec'd home for exactly this kind of explanatory text.

### D2 — Fixed legend order: states first, notes after

The scale entry is appended after the four state labels, never inserted among them, so existing
overlay tests' positional expectations for state chips are untouched and the cycle mapping's
meaning for indices 0–3 is preserved.

### D3 — Neutral "info" chip for beyond-state entries

`MapLattice.vue`: entries at index < 4 keep their state chip classes; entries at index ≥ 4 get
`local-map__legend-chip--info` — a design-token-colored neutral chip (no new hex values), with
the text label as the primary carrier, keeping the distinction independent of color. The
modular-cycling style assignment for extra entries is removed; cycling mislabels a note as a
visibility state, which is exactly the ambiguity this change must not introduce.

## Risks / Trade-offs

- [Storybook stories or browser tests pin exact legend content/order] → audit
  `stories/World/LocalMap.stories.js`, `fixtures.js`, and the local-map browser classes; update
  fixtures in the same change (showcase-coverage gate is CI-owned).
- [Client and server disagree on the 4-state prefix] → the prefix order is already a shared
  contract (the four `LEGEND_LABELS`); this change only defines behavior past its end, and one
  Vitest + one browser test pin the info-chip treatment.
- [Non-wilderness layers accidentally gain the entry] → the legend branch keys on the built
  layer; a payload test asserts grid/instance/interior legends are byte-identical to
  `LEGEND_LABELS`.

## Migration Plan

Purely additive presentation; no persisted state, no wire-schema change. Rollback = revert.

## Open Questions

- Final zh-TW wording (`每格約 10 公里` proposed; implementation decides against existing label
  register style — spec pins "states the km-per-cell scale derived from the constant", not the
  exact string).
