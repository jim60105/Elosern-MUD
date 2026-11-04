# Proposal

## Why

Resolver flee currently changes only Battlefield.fled. A mapped enemy must actually leave its cell and complete a game-time journey before it can be encountered elsewhere.

## What Changes

Replace mapped individual flee with atomic legal departure, durable passage and arrival while preserving abstract combat and the existing agility contest.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Capabilities

### New Capabilities

- `monster-journeys`.

### Modified Capabilities

- `disengage-action`.
- `wilderness-population-view`.

## Impact

Consumes landed mechanisms: stable_actor_id and reconstruct_battlefield preserve identity; regional_population owns home/local counts and PopulationTransition history; site member_ids retain living absentees; population_lifecycle already registers the merged monster_site_lifecycle clock source. Whole-cell field_enemy_roster remains the admission roster.

Attaches at world/rules/disengage.py::_handle_disengage, combat_session/rounds.py::_context_for and _finalize_resolved_round, new world/maps/monster_activity.py and existing population_lifecycle.py.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: movement-edge-history
depends-on: monster-activity-authoring

Code conflicts: global-monster-activity extends the same activity/journey owner; hostile-field-admission later inserts contact between arrival and departure. Do not edit these concurrently. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
