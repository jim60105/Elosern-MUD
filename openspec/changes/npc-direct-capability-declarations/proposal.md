# Proposal

## Why

The profession table duplicates component declarations and supplies hidden defaults. Direct records make each NPC capability and service anchor visible at its source.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Replace all profession expansion with explicit validated component declarations and per-capability bindings.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

- `npc-capability-declarations`: Replace all profession expansion with explicit validated component declarations and per-capability bindings.

### Modified Capabilities

- `profession-registries`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `import-schema`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `import-loader`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `service-anchoring`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `settlement-place-registry`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `guild-registration`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `place-attendant-hosts`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `place-driven-service-sync`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `quest-issuer-authorization`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `church-ordination`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `merchant-dialogue`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `authored-registry-references`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

world/imports/assembly.py resolves blueprint-minus-explicit overrides. profession_assembly owns attachment and binding. PlaceDefinition in world/lore/settlements/places.py owns profession and flat authored_kwargs; _hosts.py derives ServiceHostRow. Current six blueprint sets are merchant, guild_staff, guild_examiner (renamed by R), quest_issuer, attendant and clergy. All shipped schedule_template/default_tier values are null.

This is a one-engineer-day runnable slice with 6 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-service-host-identity
depends-on: authored-dialogue-generated-packages

code-conflicts: D follows H to avoid losing reuse identity when blueprints disappear. Shares places/imports/guild_config/core specs with title-authoring N; N follows D. Content batches keep profile/topic identity and may run before D; serialize docs and lore fixture changes. No active content prose is reauthored.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
