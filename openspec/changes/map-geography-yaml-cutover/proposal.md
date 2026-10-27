# Proposal

## Why

Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-geographic-sources`: Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior.

### Modified Capabilities

- `wilderness-terrain`: amend the complete affected requirement blocks for this ownership cutover.
- `continental-geography`: amend the complete affected requirement blocks for this ownership cutover.
- `lore-registries`: amend the complete affected requirement blocks for this ownership cutover.
- `wilderness-map-provider`: the provider's region label and scene association now read the published continent views.
- `lore-knowledge`: the codex's map-owned categories resolve the published composed views at call time.
- `anchor-placement`: placements resolve against the published location views rather than a removed module registry.

## Impact

content/maps/{continent,locations}.yaml; world/lore/{wilderness_regions,anchors,__init__,sync}.py; world/maps/wilderness_provider.py; continent/map/quest presenters; source contracts; docs/development/continental-geography.md

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-core-authoring-documents

code-conflicts: Serialize anchors/wilderness/room-art and lore-sync edits with later settlement/district/interior cutovers; no active NPC prose/service schema is changed here.
