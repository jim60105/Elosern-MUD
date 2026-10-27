# Proposal

## Why

Replace static coordinate targets with qualified authored references before converting their owning documents. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Replace static coordinate targets with qualified authored references before converting their owning documents.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-object-references`: Replace static coordinate targets with qualified authored references before converting their owning documents.

### Modified Capabilities

- `map-districts`: amend the complete affected requirement blocks for this ownership cutover.

## Impact

world/maps/{city_gates,room_art,bootstrap}.py; world/lore/{anchor_placement,wilderness_entry,map_districts}.py; world/lore/settlements/places*.py and _hosts.py; static quest/service declarations; web/webclient/presentation/map_quest_destinations.py; scene-address/locator adapters

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-core-sparse-geometry
depends-on: npc-title-authoring-removal

code-conflicts: Hard dependency on npc-title-authoring-removal (transitively direct-capability-declarations, host-identity and plain-name); this resolves overlapping place edits and their settlement-place-registry deltas. Serialize bootstrap/exit/presenter and knowledge-test edits with webclient-movement-alignment, without changing settlement receipts or publication ownership.
