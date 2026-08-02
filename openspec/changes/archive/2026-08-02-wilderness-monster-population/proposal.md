## Why

The onboarding journey (Beat 6) and the 新手引導 help entry direct new players to walk out of the
North Gate into the wilderness and engage a low-tier monster, but the wilderness/Virtual layer is
completely empty: `ElosernWildernessMapProvider.at_prepare_room()` only sets terrain descriptions and
scene archetypes, and no code anywhere in the project creates a `Monster` object in the wilderness. A
player who follows the guidance reaches the wilderness and finds nothing to fight, so the introductory
hunt quest (討伐低階魔物) cannot be completed through natural play — a hard gap in the deterministic,
offline-playable milestone.

## What Changes

- Introduce a deterministic wilderness monster population model: a pure, closed-form function that maps
  every wilderness coordinate to a monster tier (or none), mirroring `region_for_coordinates` /
  `terrain_description` — no LLM, no RNG, no database reads.
- Guarantee a hunting band around `capital_altoria`'s wilderness entry point (`(60, 100)`) that always
  hosts a low-tier monster, so the introductory hunt is reliably completable right after leaving the
  North Gate; further regions scale deterministically (higher tiers in harder regions).
- Add an idempotent spawn service that ensures a living monster matching the model exists at a
  wilderness coordinate, registering it in the wilderness `itemcoordinates` so it persists across room
  recycling and server restarts, and deterministically respawning a dead monster when a player next
  activates that coordinate.
- Hook the population service into `ElosernWildernessMapProvider.at_prepare_room()`, the existing seam
  that fires on every wilderness entry and step; it degrades to a no-op when no wilderness script is
  present (as in the provider's unit tests).
- No changes to combat, `engage`, quest, guild, or clock mechanics: an existing wilderness monster is
  engaged and defeated through the already-landed player-combat-session and quest-planner paths.

## Capabilities

### New Capabilities
- `wilderness-monster-population`: the deterministic coordinate→monster model and the idempotent
  spawn/registration/respawn service that populates the wilderness layer, guaranteeing huntable
  low-tier monsters near the capital entry.

### Modified Capabilities
- `wilderness-map-provider`: `at_prepare_room` additionally ensures the coordinate's deterministic
  monster population (in addition to its existing desc / scene-archetype duty).

## Impact

- `world/maps/wilderness_provider.py` — `at_prepare_room()` calls the population service (sole edit to
  an existing module).
- New `world/maps/wilderness_population.py` — pure population model and the deterministic
  spawn/registration/respawn service, the sole writer of wilderness monster presence (single-writer
  boundary: `world/maps/` owns the wilderness room/instance lifecycle).
- Tests under `world/maps/tests/`.
- No migration or backward-compatibility layer (project has zero released users).
