# Proposal

## Why

The settlement generator refuses every kind outside capital, city, town and port, and its size budget never yields fewer than two footprint cells. The village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §7) needs a one-cell map for each of about 300 villages and hamlets, with entrances that follow the roads meeting the cell.

## What Changes

- The size budget gives a `village` and a `hamlet` a one-cell footprint and a minimum outdoor node count from a single-cell tier table: 4 for a village, 2 for a hamlet. Every other kind keeps the two-cell floor.
- The generator gains a single-cell layout used only for those two kinds:
  - the footprint is the location cell, declared as a one-cell physical footprint;
  - one entrance per road cell that touches the location cell in the committed road artifact: two when a road passes through, one at the end of a spur;
  - a hamlet with no road gets one entrance by the existing gate-bearing order; a village with no road is refused;
  - nodes are the anchor, the role node and the entrance nodes, joined to the anchor by two-way roads.
- A beastfolk nation selects the tribal vocabulary and the `tribal_ring` morphology label; the layout is the same.
- The terrain-fit lint reports a village or hamlet whose gates do not match the road cells touching its cell.
- `generate --missing --nation` covers villages and hamlets and accepts an optional `--kind` filter.
- Documentation of the two tiers and the layout in `docs/development/settlement-synthesis.md`.

Human-reviewed, not tested: whether a four-node village and a two-node hamlet read well in play, and the role labels. Both are reviewed against `docs/development/settlement-synthesis.md` § Human review.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `settlement-terrain-fit`: the size budget covers the single-cell kinds, and the lint checks entrances against road contacts.
- `settlement-graph-generation`: a single-cell layout for villages and hamlets, and a kind filter for the batch.

## Impact

- `tools/settlement_synthesis/budget.py`, `generate.py`, `roles.py`, `workspace.py`, `fit_lint.py`, `__main__.py`.
- Tests: `tests/test_settlement_terrain_fit.py`, `tests/test_settlement_graph_generation.py`.
- Documentation: `docs/development/settlement-synthesis.md`, `.agents/skills/map-data-authoring/references/settlements.md`.
- No shipped settlement is generated here. No file under `world/`, `web/` or `packages/` changes, so the reference context stays current.

## Batch:

- depends-on: village-hamlet-kinds
- depends-on: single-cell-footprint-entry
- conflicts: `.agents/skills/map-data-authoring/references/settlements.md` and `tests/test_settlement_terrain_fit.py` are also changed by `single-cell-footprint-entry` (merged before this change starts).
- parallel with: `settlement-spacing-validation`, `road-spur-stage`. This change reads the road artifact through the existing decoder and needs no spur mark.
