## 1. Baseline

- [x] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [x] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing

## 2. Migration

## 3. Migrate group 1

- [x] 3.1 Migrate `web/static/webclient/js/tests/art_panel.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.2 Migrate `web/static/webclient/js/tests/character_menu.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.3 Migrate `web/static/webclient/js/tests/combat_menu.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.4 Migrate `web/static/webclient/js/tests/command_echo.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.5 Migrate `web/static/webclient/js/tests/creation_menu.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.6 Migrate `web/static/webclient/js/tests/exploration_menu.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 4. Migrate group 2

- [x] 4.1 Migrate `web/static/webclient/js/tests/hud_dock_menus.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.2 Migrate `web/static/webclient/js/tests/protocol.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.3 Migrate `web/static/webclient/js/tests/service_menu.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.4 Migrate `web/webclient-app/tests/data/breakdown_rendering.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.5 Migrate `web/webclient-app/tests/data/equipment_doll.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.6 Migrate `web/webclient-app/tests/data/skill_book.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Migrate group 3

- [x] 5.1 Migrate `web/webclient-app/tests/frame-resolvers.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.2 Migrate `web/webclient-app/tests/overlays/creation_overlay.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.3 Migrate `web/webclient-app/tests/overlays/lineage_panel.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.4 Migrate `web/webclient-app/tests/overlays/title_codex_panel.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.5 Migrate `web/webclient-app/tests/preserved_contract.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.6 Migrate `web/webclient-app/tests/store/command_echo_surfaces.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 6. Migrate group 4

- [x] 6.1 Migrate `web/webclient-app/tests/store/declarative_surfaces.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.2 Migrate `web/webclient-app/tests/store/store_dispatch_focus.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.3 Migrate `web/webclient-app/tests/world/inventory_panel.test.js` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.4 Migrate `web/webclient-app/tests/world/item_icons.test.js` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 7. Freeze-list and closure

- [x] 7.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [x] 7.2 Add the area closure test file `tests/test_data_independence_js_webclient.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 7.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [x] 7.4 Run the affected shard(s) per `.github/evennia-shards.json`, the closure test via `unittest`, and `git diff --check` (no Evennia shard is affected — the manifest is JS-only; the Node gate, the full app Vitest suite, the gate `check`, and the closure test cover the change)
