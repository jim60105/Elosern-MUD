# Proposal

## Why

Move all district declarations and stable landmarks to one YAML authority while retaining derived boundary and lighting behavior. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Move all district declarations and stable landmarks to one YAML authority while retaining derived boundary and lighting behavior.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-districts`: amend the complete affected requirement blocks for this ownership cutover.

## Impact

content/maps/districts.yaml; world/lore/map_districts.py; world/rules/map_district_lighting.py; web map presenters; tools/map_district_partition.py input adapter; docs/development/continental-geography.md

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-settlement-yaml-cutover

code-conflicts: Serializes map_districts.py, partition-input assembly, continental docs and district tests with geography and partition-core.
