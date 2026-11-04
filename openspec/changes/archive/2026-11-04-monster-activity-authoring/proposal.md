# Proposal

## Why

Birth geometry and combat behavior profiles do not declare lawful field activity or aggression. Explicit validated bindings prevent executable policy from being inferred from names or prose.

## What Changes

Publish immutable activity and aggression declarations and complete placement bindings; this authoring slice adds one validation mechanism.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Capabilities

### New Capabilities

- `monster-field-activity`.

### Modified Capabilities

None.

## Impact

Consumes landed mechanisms. Landed ecology compositions, site composition references and variant identity supply references only. Population ownership, whole-cell rosters and clock event sources are retained without runtime changes.

Attaches at world/lore/monster_placement.py, registry reference metadata and world/maps/runtime.py candidate publication.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: none

Code conflicts are global-monster-activity, which shares placement bindings and runtime publication, and mapped-monster-escape, which consumes the declarations. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
