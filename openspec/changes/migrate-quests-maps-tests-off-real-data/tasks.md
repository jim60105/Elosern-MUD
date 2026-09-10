## 1. Baseline

- [ ] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [ ] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing

## 2. Migration

## 3. Migrate group 1

- [ ] 3.1 Migrate `world/maps/tests/test_city_wilderness_roundtrip.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.2 Migrate `world/maps/tests/test_instance_reclamation.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.3 Migrate `world/maps/tests/test_instance_spawn.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.4 Migrate `world/maps/tests/test_limbo_room.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.5 Migrate `world/maps/tests/test_movement_roundtrip.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.6 Migrate `world/maps/tests/test_service_interiors.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 4. Migrate group 2

- [ ] 4.1 Migrate `world/maps/tests/test_wilderness_clock.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.2 Migrate `world/maps/tests/test_wilderness_destination.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.3 Migrate `world/maps/tests/test_wilderness_population.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.4 Migrate `world/maps/tests/test_wilderness_provider.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.5 Migrate `world/quests/tests/_compile_helpers.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.6 Migrate `world/quests/tests/_fixtures.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Migrate group 3

- [ ] 5.1 Migrate `world/quests/tests/test_acquire.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.2 Migrate `world/quests/tests/test_action_events.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.3 Migrate `world/quests/tests/test_characterization.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.4 Migrate `world/quests/tests/test_deliver.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.5 Migrate `world/quests/tests/test_describe.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.6 Migrate `world/quests/tests/test_generated_quest_store.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 6. Migrate group 4

- [ ] 6.1 Migrate `world/quests/tests/test_integration.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.2 Migrate `world/quests/tests/test_pipeline_scenarios.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.3 Migrate `world/quests/tests/test_planner.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.4 Migrate `world/quests/tests/test_room_observation.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.5 Migrate `world/quests/tests/test_runtime.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.6 Migrate `world/quests/tests/test_scene_builder.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 7. Migrate group 5

- [ ] 7.1 Migrate `world/quests/tests/test_scene_builder_flavor.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 7.2 Migrate `world/quests/tests/test_scene_builder_offline.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 7.3 Migrate `world/quests/tests/test_settlement.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 8. Freeze-list and closure

- [ ] 8.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [ ] 8.2 Add the area closure test file `tests/test_data_independence_quests.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 8.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [ ] 8.4 Run the affected shard(s) per `.github/evennia-shards.json`, the closure test via `unittest`, and `git diff --check`
