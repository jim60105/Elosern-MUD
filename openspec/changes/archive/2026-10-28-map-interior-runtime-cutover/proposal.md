# Proposal

## Why

Move all permanent interiors and topology to YAML and finish all-world immutable game publication with authoritative validation. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Move all permanent interiors and topology to YAML and finish all-world immutable game publication with authoritative validation.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-runtime-adoption`: Move all permanent interiors and topology to YAML and finish all-world immutable game publication with authoritative validation.

### Modified Capabilities

- `settlement-place-registry`: amend the complete affected requirement blocks for this ownership cutover.
- `place-driven-service-sync`: amend the complete affected requirement blocks for this ownership cutover.
- `room-art-metadata`: amend the complete affected requirement blocks for this ownership cutover.
- `authored-registry-references`: amend the complete affected requirement blocks for this ownership cutover.
- `sample-city-altoria`: amend the complete affected requirement blocks for this ownership cutover.

## Impact

content/maps/interiors/*.yaml; world/maps/{bootstrap,map_data,room_art}.py and new runtime adapter; world/lore/settlements/{places,places_*,_hosts}.py; world/rules/guild_economy.py; server/conf/at_server_startstop.py; quest/service/art/GM/presenter consumers

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-district-yaml-cutover
depends-on: map-partition-core-generation

code-conflicts: Qualified references already follows npc-title-authoring-removal, so this change owns the final amendment of settlement-place-registry and place-driven-service-sync, superseding only their geometry/prose/topology ownership. Preserve active NPC component/profile/host reuse contracts. Serialize guild_economy/bootstrap and static checks with NPC synchronization; serialize source/caller contracts and manifests with webclient movement/publication changes.
