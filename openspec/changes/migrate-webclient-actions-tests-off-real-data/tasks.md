## 1. Baseline

- [x] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [x] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing

## 2. Migration

## 3. Migrate group 1

- [x] 3.1 Migrate `web/webclient/actions/tests/test_character_actions.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.2 Migrate `web/webclient/actions/tests/test_combat_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.3 Migrate `web/webclient/actions/tests/test_combat_dispatcher.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.4 Migrate `web/webclient/actions/tests/test_creation_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.5 Migrate `web/webclient/actions/tests/test_exploration_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.6 Migrate `web/webclient/actions/tests/test_inventory_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 4. Migrate group 2

- [x] 4.1 Migrate `web/webclient/actions/tests/test_node_ids.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.2 Migrate `web/webclient/actions/tests/test_service_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.3 Migrate `web/webclient/actions/tests/test_service_validators.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.4 Migrate `web/webclient/actions/tests/test_title_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.5 Migrate `web/webclient/tests/test_art_media.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.6 Migrate `web/webclient/tests/test_webclient_contract.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Freeze-list and closure

- [x] 5.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [x] 5.2 Add the area closure test file `tests/test_data_independence_webclient_actions.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 5.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [x] 5.4 Run the affected shard(s) per `.github/evennia-shards.json`, the closure test via `unittest`, and `git diff --check`
