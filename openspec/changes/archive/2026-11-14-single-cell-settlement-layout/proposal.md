# Proposal

## Why

The settlement generator refuses every kind outside capital, city, town and port. The village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §7) needs a one-cell map for each of about 300 villages and hamlets, with entrances that follow the roads meeting the cell. `single-cell-size-budget` provides the size tier, the road contacts and the lint check; this change adds the layout.

## What Changes

- The generator gains a single-cell layout used only for `village` and `hamlet`:
  - the footprint is the location cell, declared as a one-cell physical footprint;
  - one entrance per road cell that touches the location cell in the committed road artifact: two when a road passes through, one at the end of a spur;
  - a hamlet with no road gets one entrance by the existing gate-bearing order; a village with no road is refused;
  - nodes are the anchor, the role node and the entrance nodes, joined to the anchor by two-way roads.
- A beastfolk nation selects the tribal vocabulary and the `tribal_ring` morphology label; the geometry is the same.
- `generate --missing --nation` covers villages and hamlets and accepts an optional `--kind` filter. `generate --replace` is refused for the two kinds.
- Documentation of the layout in `docs/development/settlement-synthesis.md`.

Human-reviewed, not tested: whether a four-node village and a two-node hamlet read well in play, and the role labels. Both are reviewed against `docs/development/settlement-synthesis.md` § Human review.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `settlement-graph-generation`: a single-cell layout for villages and hamlets, a kind filter for the batch, and a refused replace for the two kinds.

## Impact

- `tools/settlement_synthesis/generate.py`, `roles.py`, `workspace.py` (`analysis_input`), `__main__.py` (the `generate` command).
- Tests: `tests/test_settlement_graph_generation.py`.
- Documentation: `docs/development/settlement-synthesis.md`, `.agents/skills/map-data-authoring/references/settlements.md`.
- No shipped settlement is generated here. No file under `world/`, `web/` or `packages/` changes, so the reference context stays current.

## Batch:

- depends-on: single-cell-size-budget
- conflicts: `tools/settlement_synthesis/workspace.py`, `__main__.py` and `docs/development/settlement-synthesis.md` are also changed by `single-cell-size-budget` (merged before this change starts). `.agents/skills/map-data-authoring/references/settlements.md` is also changed by `single-cell-footprint-entry` (merged earlier).
- parallel with: `settlement-spacing-validation`, `road-spur-stage`. This change reads the road artifact through the existing decoder and needs no spur mark.
