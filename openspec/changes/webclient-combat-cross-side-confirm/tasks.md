# Tasks

Prerequisites: `webclient-combat-panel-v6` and `webclient-combat-stage-target-picking` are archived. Scope: client
presentation and input routing only; dispatch payloads, the actions' server validation and telnet stay
unchanged. Testing rules as in root `AGENTS.md` "Testing": focused commands only; browser output captured to a
scratch file; no loops over browser files; Evennia commands use a `MUD_TEST_SETTINGS=1` env file passed as
`--env-file=<file>`.

## 1. Client predicate and flow (≈2.5 h)

- [ ] 1.1 Create `web/webclient-app/stores/elosern/cross_side.js` (design D1) with the target-set expansion for
  SINGLE, SELF, AREA explicit and the three shorthands.
- [ ] 1.2 `stores/elosern/frames.js`: intercept the `target-*`, `self-confirm` and `area-confirm` submissions
  (design D2); add `confirmCrossSide` / `cancelCrossSide` and the invalidation on a `context_actions` replacement,
  playback lock and mode change. `stores/elosern/view.js`: publish `crossSideConfirm`. `stores/elosern/interaction.js`:
  claim no dock key while it is set.
- [ ] 1.3 `components/QuestionCard.vue`: `initialFocus` prop (`"yes"` default). `AppClient.vue`: the combat
  `QuestionCard` in the `choices` slot with `initial-focus="no"`, `inert` on the dock while it shows (design D3).
  `components/ActionDock.vue`: no change beyond accepting `inert` if the attribute is passed through.
- [ ] 1.4 Add `web/webclient-app/tests/store/cross_side_confirm.test.js`: the predicate over fixed inputs (hostile →
  ally / self / foe / mixed AREA / `all` / `all-enemies`; beneficial (heal and buff) → foe / ally / `all-allies`; both facts on foe,
  ally, `all`; neither fact; NONE → null) with the exact question strings; the flow (Enter, digit and
  `stageTargetPointer` activation on an ally with Attack send nothing and set `crossSideConfirm`; `confirmCrossSide`
  sends exactly one payload equal to the no-question payload; `cancelCrossSide` restores the focus key and leaves the
  AREA selection; Enter/arrows/digits with the question open dispatch nothing and move nothing; a panel replacement,
  `beatLocked` and a mode change clear it while an unrelated replacement keeps it; `stageTargetPointer` hover and
  activate are no-ops while it is open; `confirmCrossSide` and each invalidation request focus on `#action-dock`; an
  unresolvable target identity asks with the 友方與敵方 wording; Attack on a foe and heal on an ally dispatch at once). Add
  `web/webclient-app/tests/core/question_card.test.js`: `initialFocus="no"` focuses 否 on mount and after a lock
  releases; the default still focuses 是. Run
  `pnpm test -- web/webclient-app/tests/store/cross_side_confirm.test.js web/webclient-app/tests/core/question_card.test.js web/webclient-app/tests/store/stage_target_step.test.js web/webclient-app/tests/app_client_room_actions.test.js`
  and verify it passes (the last file guards the room cards' question).

## 2. Browser verification (≈1 h)

Build once: `pnpm run build`.

- [ ] 2.1 Add `test_cross_side_cast_asks_first` to `web/tests/browser/test_browser_combat_stage.py`
  `CombatStageBrowserTest`: Attack → a companion → Enter opens `[data-testid="cross-side-question"]` with role
  `dialog`, the text `確定要對友方使用〈基本攻擊〉？` and focus on 否, no `combat.cast` sent, every figure's
  `data-speaking` unchanged from the step; Escape returns to the step with focus on `#action-dock` and the same
  marker focused; Enter again then 是 sends exactly one `combat.cast` with that companion's `target_ids`; with the question open a click on a foe's
  `stage-target-hit` sends nothing; after 是 the active element is `#action-dock`; Attack on a foe sends at once with no
  dialog. Annotate it with the IDs it establishes (confirm spellings with `list`) and
  register it in `.github/browser-shards.json` beside the other `CombatStageBrowserTest` methods. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_cross_side_cast_asks_first web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_targets_are_picked_on_the_stage`
  and verify both pass.

## 3. Storybook (≈0.75 h)

- [ ] 3.1 Add the fixtures and stories of design D4. Run `pnpm run build-storybook` then
  `pnpm run showcase-coverage` and verify both succeed with `component-manifest.json` unchanged.

## 4. Documentation and gates (≈0.5 h)

- [ ] 4.1 Add the cross-side question to `web/webclient-app/AGENTS.md`'s combat section.
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`,
  `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract`,
  and `openspec validate webclient-combat-cross-side-confirm --strict`. Verify all pass.

## Workflow follow-up

- At archive, add the new ID of "A cast across sides asks for confirmation first" to
  `test_cross_side_cast_asks_first` and the modified descriptor scenario's ID stays on its existing tests.
