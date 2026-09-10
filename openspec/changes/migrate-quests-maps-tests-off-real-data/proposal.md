## Why

Quest runtime/scene/describe/settlement tests and wilderness map tests hardcode capital_altoria, introductory_hunt, healing_potion, and region keys; the shared _fixtures.py / _compile_helpers.py already poison every file that imports them.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 27 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; quest and map behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 27 flagged test files under world/quests/ and world/maps/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (14 assertion-literal files, 13 setup-literal files).
- Replace every shipped-identifier literal and shipped display-prose literal in the
  migrated files with kit constants or locally built synthetic definitions; replace
  pinned data quantities with values derived from the patched synthetic catalogs.
- Where a shared helper is part of this area's debt, rewrite its builders on kit data so
  every borrower stops inheriting shipped ids.

- Restate converted assertions as the mechanics the owning OpenSpec requirement
  describes. A test that only echoes synthetic-fixture content is deepened or deleted;
  a deleted test's `@covers_requirement` annotation moves onto the replacement test.
  A deleted test MUST name the test that exercises the same production branch; a test
  that is the only evidence for a branch is retained, never deleted for gate
  cleanliness (the aggregate coverage gate stays the CI-owned floor).
- Remove this area's debt entries from `tools/test_data_freeze.json` and add the area
  closure test in `tests/test_data_independence_quests.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `world/maps/tests/test_city_wilderness_roundtrip.py` | A |
| `world/maps/tests/test_instance_reclamation.py` | B |
| `world/maps/tests/test_instance_spawn.py` | A |
| `world/maps/tests/test_limbo_room.py` | A |
| `world/maps/tests/test_movement_roundtrip.py` | B |
| `world/maps/tests/test_service_interiors.py` | B |
| `world/maps/tests/test_wilderness_clock.py` | B |
| `world/maps/tests/test_wilderness_destination.py` | A |
| `world/maps/tests/test_wilderness_population.py` | A |
| `world/maps/tests/test_wilderness_provider.py` | A |
| `world/quests/tests/_compile_helpers.py` | B |
| `world/quests/tests/_fixtures.py` | B |
| `world/quests/tests/test_acquire.py` | A |
| `world/quests/tests/test_action_events.py` | B |
| `world/quests/tests/test_characterization.py` | B |
| `world/quests/tests/test_deliver.py` | B |
| `world/quests/tests/test_describe.py` | A |
| `world/quests/tests/test_generated_quest_store.py` | A |
| `world/quests/tests/test_integration.py` | B |
| `world/quests/tests/test_pipeline_scenarios.py` | B |
| `world/quests/tests/test_planner.py` | A |
| `world/quests/tests/test_room_observation.py` | B |
| `world/quests/tests/test_runtime.py` | B |
| `world/quests/tests/test_scene_builder.py` | A |
| `world/quests/tests/test_scene_builder_flavor.py` | A |
| `world/quests/tests/test_scene_builder_offline.py` | A |
| `world/quests/tests/test_settlement.py` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Quest and map closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/quests/ and world/maps/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 27 listed test files plus the new closure test file `tests/test_data_independence_quests.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
