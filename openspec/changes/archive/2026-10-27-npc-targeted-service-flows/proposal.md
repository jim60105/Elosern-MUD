# Proposal

## Why

Current services are room-wide and reject multiple same-class providers. A selected NPC service must keep that provider through opening and mutation.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Bind existing shop/guild/examination flows to an explicit provider and migrate current publishers, adapters and drawers atomically.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-service-menus`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `guild-registration`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

build_services_view(actor, viewed) independently resolves one staff, examiner and merchant. service_actions validators omit provider identity and _resolve_local selects a room host. Shop/guild UI consumes room-wide surfaces. request_guild_exam already accepts speaker and validates the actual counter separately from the qualified opponent. Existing host-independent quest abandonment/tracking must remain host-independent.

This is a one-engineer-day runnable slice with 5 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-examination-reception
depends-on: webclient-settlement-alignment

code-conflicts: T follows R and active webclient-settlement-alignment to preserve its service exam causal receipt; shares service_view/actions/protocol/constants/frame resolvers with P/U and active publication/immutable work. No change to protocol envelope E/R/B or publication queue ownership. Serialize shared service fixtures and schema registry.

The complete new-new and relevant active-change matrix and amendment ownership are in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`. The approved source remains unchanged.
