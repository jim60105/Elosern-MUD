# Proposal

## Why

Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-authoring-documents`: Define the complete typed authoring schema, restricted round-trip YAML codec, source discovery and runtime acceptance gates.

### Modified Capabilities

None.

## Impact

packages/map-core schema/codec/discovery/validation; proposed authoring inspection CLI used on synthetic and converted documents; no game source-format cutover in this slice

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-core-sparse-geometry

code-conflicts: Core schema changes serialize with every domain cutover. No temporary Python/YAML fallback reader is introduced.
