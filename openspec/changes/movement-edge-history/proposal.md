# Proposal

## Why

Pooled wilderness rooms cannot identify the preceding physical edge. Retreat and autonomous travel need the same legal edge and execution price as ordinary movement.

## What Changes

Persist the completed player edge and reuse canonical legal-edge pricing without changing ordinary movement costs.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Capabilities

### New Capabilities

- `movement-edge-history`.

### Modified Capabilities

None.

## Impact

Consumes landed mechanisms. Persistent individual IDs and current map registration are consumed as identities. Existing population transitions and clock/movement compensation remain authoritative; whole-cell engagement is unchanged.

Attaches at world/rules/movement_settlement.py::settle_movement and settle_relocation, world/rules/travel_cost.py::resolve_traversal_cost, typeclasses/exits.py and world/maps/wilderness_destination.py.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: none

Code conflicts are mapped-monster-escape and paid-party-retreat, which consume the new edge contract; serialize their movement/pricing edits. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
