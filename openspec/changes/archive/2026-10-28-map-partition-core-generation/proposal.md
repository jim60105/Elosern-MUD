# Proposal

## Why

Extract actual snapshot-to-partition input assembly and the existing generation algorithm into an optional independent core extra. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Extract actual snapshot-to-partition input assembly and the existing generation algorithm into an optional independent core extra.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-district-partition`: amend the complete affected requirement blocks for this ownership cutover.

## Impact

packages/map-core generation extra and lightweight partition codec/freshness; tools/map_district_partition.py; world/maps/district_partition.py game adapter; world/maps/data/district_partition.json

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-district-yaml-cutover

code-conflicts: Serializes partition algorithm/input/decoder/artifact and district tests with district/source cutovers. Editor generation integration depends on this real implementation.
