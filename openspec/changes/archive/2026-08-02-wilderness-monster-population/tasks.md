# Tasks

## 1. Pure population model

- [x] 1.1 Add `world/maps/wilderness_population.py` with a frozen `MonsterPopulation(tier, name_zh)`
  dataclass, a `CAPITAL_ENTRY_XY = (60, 100)` constant, and immutable `_REGION_TIER` /
  `_REGION_DENSITY` mappings (west/coasts/plains → low 6/3/3/3, highland forest → mid 7, deep
  forest/mountains → high 8/8), reusing the `region_for_coordinates` seam
- [x] 1.2 Implement pure `population_for_coordinates(x, y)`: Chebyshev-distance-3 hunting band around
  `CAPITAL_ENTRY_XY` always returns `low`; elsewhere presence is `(x * 92821 + y * 68917) % 10 <
  density`; name is `(x * 92821 + y * 68917) % len(example_monsters_zh)` on every branch. Verify the
  entry pin `(60, 100)` → `MonsterPopulation("low", "哥布林")` from the formula, not a special case
- [x] 1.3 Add pure `unittest.TestCase` tests for `population_for_coordinates`: same-input determinism,
  tier/name membership in `MONSTER_TIER_REGISTRY`, the entry literal pin (derived from the registry's
  `wilderness_xy` plus a literal `== (60, 100)` assertion), hunting-band coverage, a mid-tier region
  coordinate and a high-tier region coordinate returning their tiers, a low-density coordinate
  returning `None`, and a source guard asserting no `world.ai`/`random`/HTTP dependency

## 2. Spawn / respawn service

- [x] 2.1 Implement `ensure_population(wilderness, coordinates)`: set `db.population_key =
  "wilderness:{x}:{y}"` on every created monster and reconcile ONLY marker-matching monsters — when
  the model returns `None`, delete/pop matching monsters; when it returns a population, reconcile to
  exactly one living matching monster (delete dead/surplus, then create one `Monster` with
  `threat_tier` set, `apply_monster_tier("floor")` applied, innate-only skills, registered in
  `wilderness.db.itemcoordinates[monster] == coordinates`, `.location` set to the active room at that
  coordinate if one exists)
- [x] 2.2 Add `EvenniaTest` integration tests under `world/maps/tests/test_wilderness_population.py`
  for the reconcile branches (empty→spawn, duplicate-free idempotency, dead→replace, stale→cleanup)
- [x] 2.3 Add a test proving a foreign monster (no matching `population_key`) at the coordinate is
  never deleted, moved, or modified by reconciliation
- [x] 2.4 Add a test proving a registered monster survives room recycling: vacate and recycle the
  room, re-enter the coordinate, and assert the same monster is re-attached to the active room
- [x] 2.5 Add a `sync_wilderness()` re-run integration test: enter `(60, 100)`, record the monster
  dbref, re-run `sync_wilderness()`, and assert exactly one `Monster` remains at that coordinate with
  the same dbref and location — the startup re-run path must not duplicate or replace a living monster

## 3. Provider hook

- [x] 3.1 Extend `ElosernWildernessMapProvider.at_prepare_room` to call
  `ensure_population(room.wilderness, coordinates)` when `room.wilderness` resolves, with a deferred
  import to avoid a load-time cycle; no-op when no wilderness script is attached
- [x] 3.2 Extend the existing `world/maps/tests/test_wilderness_provider.py` provider tests: assert
  `at_prepare_room` on a scriptless `TerrainRoom` stays a population no-op, and assert the population
  hook fires through real wilderness entry (a monster appears at the entry coordinate)

## 4. End-to-end onboarding verification

- [x] 4.1 Update `world/maps/tests/test_city_wilderness_roundtrip.py` so the round-trip
  bookkeeping assertion no longer requires `dict(script.db.itemcoordinates) == {}`: assert `char1` is
  absent from `itemcoordinates` (the return-exit cleanup this test exists to prove) while a marker
  `Monster` remains registered at the entry coordinate — preserving the original leak-check intent
  under the new persistent-population contract
- [x] 4.2 Add an integration test walking the onboarding hunt from the North Gate: register the
  player, accept `introductory_hunt` through the player-facing `CmdGuildAccept` path, `sync_grid` +
  `sync_wilderness`, traverse the `荒野` gate, confirm a living `Monster` is present at the entry
  coordinate, and complete the quest through the ordinary command path (`CmdEngage` then
  `CmdCast basic_attack` with `roll_d100` patched to 100 for a decisive deterministic hit), asserting
  the quest record's completed state
- [x] 4.3 Annotate every test that establishes a new main-spec requirement with
  `@covers_requirement` using canonical IDs from `tools.spec_traceability list`, and ensure no main
  requirement is left uncovered

## 5. Spec sync and verification gate

- [x] 5.1 After implementation, sync the delta specs into main specs (`openspec/specs/
  wilderness-monster-population/spec.md` new; `openspec/specs/wilderness-map-provider/spec.md`
  updated) so the new requirement IDs exist for traceability, and verify the diff is identical to the
  deltas
- [x] 5.2 Run the focused suites (`world/maps/tests`, `world/rules/tests/test_combat_session.py`,
  `world/quests/tests`, `commands/tests`, `typeclasses/tests`) and fix failures
- [x] 5.3 Run the full `evennia test --settings settings.py .` suite plus
  `unittest discover tests` with the same `OPENSPEC_TEST_EVIDENCE` path, then run
  `python -m tools.spec_traceability verify --evidence` and confirm `git diff --check` is clean
