# Proposal

## Why

Real populations currently remain at their birth coordinates until an explicit owner moves them. Bounded game-time decisions must evolve unobserved groups without replacing their living IDs.

## What Changes

Enable seeded bounded solitary wandering and cohesive group journeys globally through the existing population clock source.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-field-activity`.
- `monster-journeys`.
- `regional-population`.
- `wilderness-monster-population`.
- `world-clock`.

## Impact

Consumes landed mechanisms. The landed home-owned ceiling already covers detached/unlocated living individuals and must not be reimplemented. PopulationPresence/PopulationTransition, historical protected_cells and identity-based site clearing supply accounting. The preceding journey change supplies real durable movement. Existing whole-cell membership remains independent of movement groups.

Attaches at world/maps/regional_population.py::commit_population_wave, monster_sites.py::_populate, monster_activity.py and population_lifecycle.py::settle_population_lifecycle.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: mapped-monster-escape

Code conflicts run in ownership order, where mapped-monster-escape owns the journey engine first, incapacitated-hostile-rounds consumes physiology ownership next and hostile-field-admission subsequently changes same-tick contact ordering. Shared lore and shard changes serialize. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
