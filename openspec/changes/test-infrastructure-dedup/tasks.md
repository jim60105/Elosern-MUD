## 0. Ground rules (apply to every task)

- Land this change LAST (after `rules-wallet-rollback-helpers` and `rules-handler-dedup`) so
  no sibling is mid-edit in `world/rules/tests/test_clock.py`/`test_cast_settlement.py`.
- HARD: no `test_*.py` file is renamed, moved, added, or deleted in `commands/`, `server/`,
  `typeclasses/`, `world/`, `web/webclient/` — `.github/evennia-shards.json` stays untouched
  and `tests.test_evennia_test_optimization_contract` must stay green throughout.
- HARD: every `@covers_requirement` stays a literal-ID decorator on a discoverable `test_*`
  method IN ITS ORIGINAL FILE. `uv run --locked python -m tools.spec_traceability check` is
  run after every step-group, not just at the end.
- Evennia tests: `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input. Browser journeys: one
  class/file locally, never the full managed browser suite.

## 1. Data-independence base (17 files)

- [ ] 1.1 Diff the family to enumerate variants exactly: read
  `tests/_data_independence_base.py`'s future inputs — `git grep -l "test_migrated_files_hold_no_ledger_exemption" tests/`
  (expect 12), `... "test_migrated_files_carry_zero_findings"` (16), `... "test_no_violation_naming_a_manifest_file"` (12),
  `... "test_freeze_ledger_seed_array_untouched_by_the_migration"` (17),
  `... "test_gate_is_green_and_reports_no_violation_for_migrated_files"` (4); diff two
  same-named bodies to confirm they are verbatim-identical modulo manifest constants; record
  the "hash-groups" split inside `test_migrated_files_carry_zero_findings` and
  `test_freeze_ledger_seed_array_untouched_by_the_migration`.
- [ ] 1.2 Create `tests/_data_independence_base.py` with
  `DataIndependenceContractMixin` and the five `assert_*` methods per design D1 (bodies =
  the union of the copies; `setUp` loads the ledger once via `test_data_lint.load_ledger`
  and asserts `fatal == []`; manifest variants become parameters/class-attributes).
- [ ] 1.3 Convert the 17 `tests/test_data_independence_*.py` files to mixin + thin decorated
  shells, keeping each file's docstring, manifest constants (`MIGRATED_FILES`,
  `NEW_HELPER_FILES`, `BEHAVIOR_FILES`), class name, literal `@covers_requirement` IDs, and
  every shell's `test_*` name. Convert ONE file first (`tests/test_data_independence_rules_guild.py`)
  and verify: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_data_independence_rules_guild`
  and `uv run --locked python -m tools.spec_traceability check`; then sweep the remaining 16
  and verify: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_data_independence_rules_creation tests.test_data_independence_browser tests.test_data_independence_ai_server tests.test_data_independence_art_imports tests.test_data_independence_js_webclient tests.test_data_independence_webclient_actions tests.test_data_independence_webclient_presentation tests.test_data_independence_skills tests.test_data_independence_rules_sexual tests.test_data_independence_rules_party tests.test_data_independence_rules_monster tests.test_data_independence_rules_knowledge tests.test_data_independence_rules_guild tests.test_data_independence_rules_equipment tests.test_data_independence_rules_combat tests.test_data_independence_quests tests.test_data_independence_commands`.

## 2. Showcase evidence run_npm / build-lock boilerplate

- [ ] 2.1 Add public `run_npm(args, timeout)` (and `run_node` if any file defines it
  separately — check `grep -n "def run_node" web/webclient/tests/`) to
  `web/webclient/tests/_showcase_build.py`, plus a shared `ShowcaseEvidenceMixin`
  (or `build_for(cls)` helper) wrapping the `showcase_build_lock()`/`ensure_app_dist()`
  `setUpClass` pattern.
- [ ] 2.2 Delete the local `run_npm` defs and collapse `setUpClass` in the 7 evidence
  modules (`test_vue_showcase_evidence.py`, `test_vue_store_evidence.py`,
  `test_vue_breakdown_evidence.py`, `test_vue_showcase_action_evidence.py`,
  `test_vue_showcase_data_evidence.py`, `test_vue_showcase_overlays_evidence.py`,
  `test_vue_showcase_world_evidence.py`; `test_vue_hud_drawer_evidence.py` only if it carries
  a copy). Do not touch their `@covers_requirement`-decorated method bodies. Verify (these
  drive npm builds — run the label group once; ~10 min budget):
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_store_evidence`
  then `... web.webclient.tests.test_vue_showcase_evidence`.
  Then `uv run --locked python -m tools.spec_traceability check`.

## 3. Browser harness mixins

- [ ] 3.1 Add `ManagedServerTearDownMixin` (variant-b order per design D3) and
  `wait_command_field_released(page, timeout=30000)` to `web/tests/browser/harness.py`.
- [ ] 3.2 Convert the identical-tearDown browser classes to the mixin; keep a 3-line
  variant-a override in `test_browser_action_feedback.py` and `test_browser_creation.py`
  (the two whose order reads `server` before `super().tearDown()`). Delete the two
  `_wait_command_field_released` copies (`test_browser_input_narrative.py:60`,
  `test_browser_shell.py:46`) importing the harness function.
  NOTE: `web/tests/browser/test_browser_wait_helper.py` tests the UNRELATED
  `wait_for_store_state` helper (`browser_helpers.py`) and never touches
  `wait_command_field_released` or `ManagedServerTearDownMixin` — running it proves nothing
  about 3.1 and must not be cited as coverage. Verification instead: (1) a small new
  plain-`unittest` self-test INSIDE `harness.py`'s owning module is not possible (browser
  budget), so add one cheap non-browser test module `web/tests/browser/test_harness_mixins.py`
  — a NON-browser `unittest.TestCase` that drives `ManagedServerTearDownMixin.tearDown` with a
  `Mock()` server and drives `wait_command_field_released` against a fake page object (same
  fake-locator pattern as `test_browser_wait_helper.py` uses for `wait_for_store_state`);
  register nothing in the shard manifest (browser package `web.tests.browser` is already a
  label — check first whether a new non-journey module under it must be listed; if the shard
  contract sweeps `web/tests/browser/`, add the label in the same commit as AGENTS.md
  requires); and (2) one converted journey class, e.g.
  `... web.tests.browser.test_browser_synth_journey.<OneCheapClass>` — pick the smallest
  existing class in that file.

## 4. `_raw_attribute` SQL probe

- [ ] 4.1 Create `world/tests/raw_attributes.py::raw_attribute_value(obj, key)` with the
  union SQL body (read `world/rules/tests/test_clock.py:820-840` for the fullest docstring).
  Replace each of the six class methods with a one-line delegate in
  `world/maps/tests/test_instance_reclamation.py:507`, `world/quests/tests/test_deadlines.py:317`,
  `world/rules/tests/test_cast_settlement.py:157`, `world/rules/tests/test_clock.py:820`,
  `world/rules/tests/test_npc_schedule_runtime.py:833`,
  `world/rules/tests/test_shop_clock_sources.py:262` (import inside each test module; keep
  method name + per-file docstring). Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_clock` and
  `... world.rules.tests.test_cast_settlement` and
  `... world.quests.tests.test_deadlines` and `... world.maps.tests.test_instance_reclamation`.

## 5. Close-out

- [ ] 5.1 Shard contract green with an untouched manifest:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.2 `uv run --locked python -m tools.spec_traceability check` and
  `uv run --locked python -m tools.observability_lint check` pass; freeze list diff empty.
- [ ] 5.3 `uv run --locked python -m tools.test_data_lint check` green (the gate the
  data-independence family guards must be untouched by the extraction).
- [ ] 5.4 `git diff --check` clean; `git status` shows no new/renamed `test_*.py` anywhere.
