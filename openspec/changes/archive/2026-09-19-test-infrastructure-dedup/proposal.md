## Why

The test corpus carries the program's largest absolute duplication (~2,000 lines):

- `tests/test_data_independence_*.py` ×17 files: five test bodies repeated verbatim across
  the family (`test_migrated_files_hold_no_ledger_exemption` ×12,
  `test_migrated_files_carry_zero_findings` ×16, `test_no_violation_naming_a_manifest_file`
  ×12, `test_freeze_ledger_seed_array_untouched_by_the_migration` ×17,
  `test_gate_is_green_and_reports_no_violation_for_migrated_files` ×4) with only the
  `MIGRATED_FILES`/`NEW_HELPER_FILES` manifests differing. When the ledger contract's probe
  mechanics change, seventeen files must change in lockstep — and one forgotten file turns a
  green suite into a lying suite.
- `web/webclient/tests/`: `run_npm` is duplicated verbatim in 7 evidence modules
  (`test_vue_showcase_evidence.py`, `test_vue_store_evidence.py`,
  `test_vue_breakdown_evidence.py`, `test_vue_showcase_{action,data,overlays,world}_evidence.py`,
  plus `test_vue_hud_drawer_evidence.py` where present); the `setUpClass`
  build-lock/`ensure_*` boilerplate repeats ×6.
- `web/tests/browser/`: the managed-server `tearDown` repeats across ~11 test modules in two
  orderings, `_wait_command_field_released` ×2 (`test_browser_input_narrative.py:60`,
  `test_browser_shell.py:46`), and the `_raw_attribute` SQL probe ×6 in
  `world/{maps,quests,rules}/tests/` (`test_instance_reclamation.py:507`,
  `test_deadlines.py:317`, `test_cast_settlement.py:157`, `test_clock.py:820`,
  `test_npc_schedule_runtime.py:833`, `test_shop_clock_sources.py:262`).

## What Changes

- New `tests/_data_independence_base.py`: `DataIndependenceContractMixin` +
  `assert_*` functions parameterized by each module's manifest constants. **Hard
  constraint:** every existing file keeps its own discoverable `test_*` methods with literal
  `@covers_requirement` IDs (traceability requires literals — no dynamic generation), each a
  2-5 line shell delegating to the mixin. File names do not change.
- `run_npm`/`run_node` move into the existing `web/webclient/tests/_showcase_build.py`
  (alongside `showcase_build_lock`/`ensure_app_dist`); the 7 evidence modules import it. The
  `setUpClass` bodies collapse to a mixin `_showcase_build.py::ShowcaseEvidenceMixin` (or a
  module-level `setUp_class(cls)` call) — file names unchanged.
- `web/tests/browser/harness.py` gains `ManagedServerTearDownMixin` and
  `wait_command_field_released(page, timeout=30000)`; the two ordering variants of the
  current `tearDown` are preserved (design D3).
- New `world/tests/raw_attributes.py::raw_attribute_value(obj, key)`; the six `_raw_attribute`
  copies become `def _raw_attribute(self, obj, key): return raw_attribute_value(obj, key)`
  delegates — keeping the test-class method name any assertion or subTest message references.
- Zero test semantics change; no shard-manifest edit (no module renamed/moved; helpers are
  underscore/non-test modules, a shape the ownership contract already tolerates —
  `_showcase_build.py`, `_combat_session_helpers.py`, `_dialogue_helpers.py` exist today).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — `skip_specs: true`. The `test-data-independence` requirements keep their current
wording and stay covered: the literal `@covers_requirement` IDs move onto the thin shells in
the same files, so `tools.spec_traceability check` resolves identically (annotations stay on
discoverable `test_*` methods with real assertions — the mixin keeps them real, just
shared).

## Impact

`tests/test_data_independence_*.py` ×17 → thin shells + new `tests/_data_independence_base.py`;
`web/webclient/tests/_showcase_build.py` + 7 evidence modules;
`web/tests/browser/harness.py` + ~11 `test_browser_*.py`; six `_raw_attribute` test files +
new `world/tests/raw_attributes.py`. No production module, no command surface, no
`.github/evennia-shards.json` change.

## Batch

- depends-on: `rules-wallet-rollback-helpers` and `rules-handler-dedup` SHOULD merge BEFORE
  this change (both may edit `world/rules/tests/test_clock.py` / `test_cast_settlement.py`,
  the same files this change edits for `_raw_attribute` — textual collision avoided by
  ordering; also this change must not churn a test file another change is patching).
- Independent of `webclient-presentation-push-factory`, `art-path-confinement-and-ai-guardrails`,
  `webclient-frontend-utils` (the frontend change touches `web/webclient-app/**` only; this
  one touches Python test files).
- Overlap with the three active changes: `divine-mystery-catalog` edits
  `.github/evennia-shards.json` (append-only) and `world/rules/tests/test_divine_mystery_gate.py`;
  this change touches neither file. `martial-arts-catalog` / `elementless-damage-effect`
  touch `world/skills/tests/*` only — disjoint. Land LAST anyway (wave D convention).

## Non-goals

- `_in_exploration_mode` (`presentation/character.py:658` vs `affordances.py:188`):
  explicitly out of scope — the audit's own rule ("only extract if byte-identical semantics")
  is not satisfied; the two copies guard different surfaces.
- `_db_safe` (`world/lore/sync.py` vs `world/quests/compile.py`): leave as-is (deliberate
  divergence, documented in the compile.py comment).
- `browser_helpers.py` / `browser_base.py` already exist; do NOT create a competing helper
  home — browser additions go to `harness.py`/`browser_helpers.py` as the audit specifies.
