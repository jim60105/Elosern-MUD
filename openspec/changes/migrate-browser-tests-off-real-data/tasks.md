## 1. Baseline

- [x] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [x] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing
- [x] 1.3 Wire `install_synthetic_catalogs()` into `web/tests/browser/browser_settings.py` behind the kit flag and add a seed smoke test proving the seeded DB + server resolve one `t_` key end to end before migrating any journey file

## 2. Migration

## 3. Migrate group 1

- [ ] 3.1 Migrate `web/tests/browser/browser_helpers.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.2 Migrate `web/tests/browser/browser_settings.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.3 Migrate `web/tests/browser/seed.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.4 Migrate `web/tests/browser/test_browser_art.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.5 Migrate `web/tests/browser/test_browser_combat.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.6 Migrate `web/tests/browser/test_browser_combat_rejection.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 4. Migrate group 2

- [ ] 4.1 Migrate `web/tests/browser/test_browser_contextual_hud.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.2 Migrate `web/tests/browser/test_browser_creation.py` (tier S, re-derive pinned quantities from the synthetic catalog): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.3 Migrate `web/tests/browser/test_browser_exploration.py` (tier S, re-derive pinned quantities from the synthetic catalog): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.4 Migrate `web/tests/browser/test_browser_input_narrative.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.5 Migrate `web/tests/browser/test_browser_inventory_actions.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 4.6 Migrate `web/tests/browser/test_browser_inventory_grid.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Migrate group 3

- [ ] 5.1 Migrate `web/tests/browser/test_browser_lineage.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.2 Migrate `web/tests/browser/test_browser_local_map.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.3 Migrate `web/tests/browser/test_browser_pointer.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.4 Migrate `web/tests/browser/test_browser_services.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.5 Migrate `web/tests/browser/test_browser_shell.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.6 Migrate `web/tests/browser/test_browser_title_codex.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 6. Migrate group 4

- [ ] 6.1 Migrate `web/tests/browser/test_vue_foundation.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 7. Freeze-list and closure

- [ ] 7.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [ ] 7.2 Add the area closure test file `tests/test_data_independence_browser.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 7.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [ ] 7.4 Run the affected shard(s) per `.github/evennia-shards.json`, the closure test via `unittest`, and `git diff --check`
