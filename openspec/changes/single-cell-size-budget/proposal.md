# Proposal

## Why

The settlement size budget rejects every kind outside capital, city, town and port and never yields fewer than two footprint cells, and nothing checks that a one-cell settlement's gates match the roads that reach it. The village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §7) needs both before the single-cell generator layout can be built. This change is the first half of the design's "single-cell layout and two tiers" item; `single-cell-settlement-layout` is the second half. The item was split to keep each change within one working day.

## What Changes

- The size budget gives a `village` and a `hamlet` a one-cell footprint and a minimum outdoor node count from a single-cell tier table: 4 for a village, 2 for a hamlet. Every other kind keeps the two-cell floor and its tier tables.
- The synthesis workspace can list the road cells that touch a location cell in the committed road artifact (its road contacts).
- The terrain-fit lint reports a village or hamlet whose gates do not match its road contacts.
- Documentation of the two tiers and the new lint finding.
- The generator still refuses the two kinds after this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `settlement-terrain-fit`: the size budget covers the single-cell kinds, and the lint checks single-cell entrances against road contacts.

## Impact

- `tools/settlement_synthesis/budget.py`, `workspace.py`, `fit_lint.py`, `__main__.py` (the `budget` and `lint` commands only).
- Tests: `tests/test_settlement_terrain_fit.py`.
- Documentation: `docs/development/settlement-synthesis.md`.
- No file under `world/`, `web/` or `packages/` changes, so the reference context stays current.

## Batch:

- depends-on: village-hamlet-kinds
- depends-on: single-cell-footprint-entry
- conflicts: `tests/test_settlement_terrain_fit.py` is also changed by `single-cell-footprint-entry` (merged before this change starts). `tools/settlement_synthesis/workspace.py`, `__main__.py` and `docs/development/settlement-synthesis.md` are also changed by `single-cell-settlement-layout`, which follows this change.
- parallel with: `settlement-spacing-validation`, `road-spur-stage`. This change reads the road artifact through the existing decoder and needs no spur mark.
