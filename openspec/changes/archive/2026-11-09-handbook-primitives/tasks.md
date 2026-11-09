# Tasks: handbook-primitives

Run pnpm commands from the repository root, vitest as `pnpm exec vitest run <path>`, and Python tests with `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb <label>` (`<file>` contains `MUD_TEST_SETTINGS=1`). Fixtures are synthetic.

## 1. DetailFooter extraction

- [x] 1.1 Create `components/DetailFooter.vue` and switch `QuestDetail.vue` to it per design D1. Update the class assertion in `tests/world/quest_detail.test.js`. Verify with `pnpm exec vitest run web/webclient-app/tests/world/quest_detail.test.js web/webclient-app/tests/world/quest_drawer.test.js`. Every existing test passes.
- [x] 1.2 Add `tests/components/detail_footer.test.js` covering every scenario of the DetailFooter requirement: a disabled button is focusable with `aria-disabled` and emits nothing; a toggle uses native `disabled`; `press` is emitted once per activation; `focus(key)` focuses that button; `reasonRole="alert"` renders. Verify with vitest on that file.
- [x] 1.3 Run the quest-drawer browser footer methods once, each on its own: the methods in `web/tests/browser/test_browser_services_quest_drawer.py` that click `quest-drawer__abandon` or `quest-drawer__track` (find them with `git grep -n "quest-drawer__abandon\|quest-drawer__track" web/tests/browser`). Use `uv run --locked python -m web.tests.browser.unittest_driver <module>.<Class>.<method>` with output captured to a scratch file. All pass.

## 2. TileWall, CodexEmblem, CodexDetail

- [x] 2.1 Port `TileWall.vue` per design D2 and add `tests/handbook/tile_wall.test.js` covering every scenario of the TileWall requirement. Verify with vitest on that file.
- [x] 2.2 Add the emblem paths and `CodexEmblem.vue` per design D3, with `tests/handbook/codex_emblem.test.js` (a known name renders its path; an unknown name renders the `emblem_unknown` path). Verify with vitest.
- [x] 2.3 Create `CodexDetail.vue` per design D4 with `tests/handbook/codex_detail.test.js`: it renders ribbon, title, subtitle and sections; a grade renders `GradeGem`, else the emblem; `locked` draws the silhouette marker (`data-locked="true"`); the `hero` slot replaces the face; a null `footer` renders no footer; a footer `press` is re-emitted; a null detail renders `handbook__detail-empty`. Verify with vitest.
- [x] 2.4 Run `grep -n -E "detail-footer|tile-wall|codex-detail|codex-emblem" web/webclient-app/styles/app-shell.css` and expect no output.

## 3. Stories, manifest, evidence

- [x] 3.1 Add the stories and manifest entries per design D5. Verify with `pnpm run build-storybook && pnpm run showcase-coverage` and the focused labels for the four `web.webclient.tests.test_vue_showcase_*_evidence` modules.
- [x] 3.2 Create the evidence bridge per design D5 and register it in `.github/evennia-shards.json`. Verify with the focused labels `web.webclient.tests.test_vue_handbook_evidence` and `tests.test_evennia_test_optimization_contract`.
- [x] 3.3 Run `uv run --locked python -m tools.test_data_lint check`, the focused label `tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate --change handbook-primitives`, and `openspec validate handbook-primitives --strict`. All pass. The new testids are only referenced from vitest and Storybook, not from browser tests, so the frozen audit needs no edit. If `tests.test_webclient_frozen_contract` reports otherwise, add a `handbook__` family row to `docs/development/webclient-vue-frozen-contract-audit.md` §2.3.

## Workflow follow-up

- At archive, after the sync, annotate `VueHandbookEvidenceTest`'s two methods with the IDs of "TileWall is a grouped roving-focus listbox" and "DetailFooter renders descriptor buttons and a committed reason", taken from `uv run --locked python -m tools.spec_traceability list`. Then run `tools.spec_traceability check` without `--change`.
