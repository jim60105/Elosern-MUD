# Proposal

## Why

Host reuse currently inspects the first blueprint component and service IDs. Component order can therefore alter identity, and synchronization can move a reused person or delete unrelated state.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Reuse source-managed hosts by canonical profile provenance and reconcile owned capability configuration without resetting live state.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

- `npc-service-host-identity`: Reuse source-managed hosts by canonical profile provenance and reconcile owned capability configuration without resetting live state.

### Modified Capabilities

- `guild-registration`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `quest-issuer-authorization`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `sample-city-altoria`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `npc-identity-titles`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

guild_economy._row_anchor_class reads profession.components[0]; _find_service_host searches its service_id; _sync_service_host relocates reused hosts. _converge_service_hosts inspects all component IDs and npc_title to delete residue. Existing hosts already carry canonical `npc_profile_key` through NPC_PROFILE_PROVENANCE_ATTRIBUTE. Stock initialization belongs to _initialize_merchant_stock, outside component assembly.

This is a one-engineer-day runnable slice with 4 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-examination-reception

code-conflicts: H follows R because the managed vocabulary uses reception. D owns later input replacement; N/P/GM share guild_economy/identity/specs. Existing authored dialogue content uses profile identity unchanged; no topic/body edit is needed. Serialize deletion callback edits with authored-dialogue-refresh-lifecycle and webclient-publication-settlements.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
