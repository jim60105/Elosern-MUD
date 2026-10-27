# Proposal

## Why

Extract the sparse graph, coordinate and deterministic terrain calculations into an independent Python core and migrate their game callers. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Extract the sparse graph, coordinate and deterministic terrain calculations into an independent Python core and migrate their game callers.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-geometry-model`: Extract the sparse graph, coordinate and deterministic terrain calculations into an independent Python core and migrate their game callers.

### Modified Capabilities

None.

## Impact

packages/map-core; world/maps/{sparse_graph,map_data,bootstrap,wilderness_provider,wilderness_reachability}.py; world/lore/{anchors,wilderness_entry,map_districts}.py; typeclasses/exits.py; map presenters and movement/route callers; root dependency metadata

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: none

code-conflicts: Serialize shared map algorithms, synthetic factories, traceability and dependency metadata with the later source cutovers. No active proposal owns these algorithms.
