# Tasks

Test commands follow AGENTS.md: run each command on its own. `EV` stands for
`uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`.

## 1. Helpers (design D1)

- [x] 1.1 Confirm the equality before editing. In a scratchpad script (not committed),
  publish the map world, then compare the old sorted-first `CITY_GATE_REGISTRY` gate ref
  with the first gate destination of the sorted-first `WILDERNESS_ENTRY_REGISTRY`. If they
  differ, stop and report.
- [x] 1.2 Add `entrance_refs` and `first_entrance_ref` to `world/tests/geography_fixture.py`,
  exactly as in D1.

## 2. Call sites (design D2)

- [x] 2.1 Edit `commands/tests/test_localized/test_xyz_grid_and_help.py`,
  `web/webclient/actions/tests/test_node_ids.py`,
  `web/webclient/actions/tests/test_exploration_actions/test_move_and_look.py` and
  `web/webclient/presentation/tests/test_affordances/test_vocabulary.py`. Then run
  `EV commands.tests.test_localized.test_xyz_grid_and_help`,
  `EV web.webclient.actions.tests.test_node_ids`,
  `EV web.webclient.actions.tests.test_exploration_actions.test_move_and_look` and
  `EV web.webclient.presentation.tests.test_affordances.test_vocabulary`, one per
  command. All must pass.
- [x] 2.2 Edit `web/webclient/presentation/tests/test_local_map/_support.py` and
  `test_gateway_resolution.py`. Then run every module in
  `web/webclient/presentation/tests/test_local_map/`, one `EV` command per module. All
  must pass.
- [x] 2.3 Edit `world/rules/tests/test_map_knowledge_integration/_support.py`. Then run
  each module of that package with `EV`. All must pass.
- [x] 2.4 Edit `world/tests/synthetic_data/vocab.py`. Then
  `EV world.tests.test_synthetic_data` must pass.
- [x] 2.5 Edit `web/tests/browser/browser_helpers.py`,
  `web/tests/browser/seed/minimap_fixture.py` and
  `web/tests/browser/seed/exploration_fixture.py`. Run `pnpm run build`, then the
  minimap browser class (first file of
  `rg -l "ELOSERN_BROWSER_MINIMAP" web/tests/browser/test_*.py`) and the exploration
  browser class (first file of `rg -l "ELOSERN_BROWSER_EXPLORATION" web/tests/browser/test_*.py`)
  with `uv run --locked python -m web.tests.browser.unittest_driver <module>`. Both must pass.

## 3. Verification

- [x] 3.1 `uv run --locked python -m tools.contract_gate` and
  `uv run --locked python -m tools.test_data_lint check` pass.
- [x] 3.2 `git diff` shows no changed assertion, only probe expressions, imports and
  comments.
- [x] 3.3 `openspec validate entrance-probe-fixtures --strict` passes.
