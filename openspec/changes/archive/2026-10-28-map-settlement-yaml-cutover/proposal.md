# Proposal

## Why

Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-settlement-sources`: Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration.

### Modified Capabilities

- `anchor-placement`: amend the complete affected requirement blocks for this ownership cutover.
- `limbo-one-way-gates`: amend the complete affected requirement blocks for this ownership cutover.
- `wilderness-gateway`: amend the complete affected requirement blocks for this ownership cutover.
- `sample-city-altoria`: amend the complete affected requirement blocks for this ownership cutover.
- `village-ciaran-map`: amend the complete affected requirement blocks for this ownership cutover.
- `grid-room-sync`: amend the complete affected requirement blocks for this ownership cutover.

## Impact

content/maps/settlements/*.yaml; world/maps/{map_data,altoria_capital,village_ciaran,bootstrap,city_gates,room_art}.py; world/lore/{anchor_placement,anchors,wilderness_entry,sync}.py; typeclasses/exits.py; grid provider/route/knowledge/presenter consumers

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-qualified-static-references
depends-on: map-geography-yaml-cutover

code-conflicts: Follows qualified references to avoid half-migrated targets. Serialize bootstrap, lore sync, source-contract tests and manifests with interiors/districts; preserve active webclient movement and settlement publication facts.
