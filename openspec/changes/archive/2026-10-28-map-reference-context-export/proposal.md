# Proposal

## Why

Export a deterministic authoritative static-reference closure and support independent freshness checking for safe editor deletion. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Export a deterministic authoritative static-reference closure and support independent freshness checking for safe editor deletion.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-external-reference-context`: Export a deterministic authoritative static-reference closure and support independent freshness checking for safe editor deletion.

### Modified Capabilities

None.

## Impact

proposed tools/map_reference_context.py; content/map-reference-context.json; packages/map-core reference-context codec/checker; authoritative quest/service/scene/art/lore declarations; CI planning for check integration; docs/development/map-editor.md

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-interior-runtime-cutover

code-conflicts: Serialize all later static-reference/source changes with regeneration of this committed output. NPC producers and titles must already be final through the runtime prerequisite; active UI-only proposals have no semantic dependency.
