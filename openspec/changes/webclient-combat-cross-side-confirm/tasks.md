# Tasks

Prerequisite: `webclient-combat-stage-target-picking` is archived on master. Scope: one read-only presenter fact pair
plus client presentation and input routing; dispatch payloads, the actions' server validation and telnet stay
unchanged. Testing rules as in root `AGENTS.md` "Testing": focused commands only; browser output captured to a
scratch file; no loops over browser files; Evennia commands use a `MUD_TEST_SETTINGS=1` env file passed as
`--env-file=<file>`.

## 1. Server fact and wire mirrors (≈2 h)

- [ ] 1.1 `world/rules/combat_view.py`: add `harms` and `restores` to `SkillDescriptorView` (docstring included) and
  derive them in `_build_skills` from `skill.parsed_effects` × `skill.effect_policies` with the `SELECTED` audience
  (design D1).
- [ ] 1.2 `web/webclient/presentation/combat_panel.py`: emit both in `_serialize_skill` and require both as booleans in
  the skill validator's exact field set. `web/static/webclient/js/elosern/protocol/panels/combat.js`: require both in
  `validateSkill` (booleans). Update the hand-written combat skill descriptors these validators see: find them with
  `grep -rln "\"shorthands\"\|shorthands:" web/webclient/presentation/tests web/static/webclient/js/tests web/webclient-app/tests web/webclient-app/stories web/tests/browser/_journey_support.py world/rules/tests/test_combat_view.py`
  and add `harms`/`restores` (prefer the shared builders: `web/webclient/presentation/tests/test_combat_panel/_support.py`,
  `web/static/webclient/js/tests/protocol_fixtures.js`, `web/webclient-app/stories/fixtures/combat_stage.js`).
- [ ] 1.3 Tests: in `world/rules/tests/test_combat_view.py` assert the six cases of the delta scenario "Each skill
  declares whether it harms or restores its chosen targets" (`basic_attack`, `heal`, the cleanse skill, an
  `ENEMIES`-routed damage skill, a buff-only skill, and a synthetic both-facts skill in the module's existing registry
  fixture style); in `web/webclient/presentation/tests/test_combat_panel/test_schema.py` assert the server validator
  rejects a missing and a non-boolean `harms`/`restores`; in `web/static/webclient/js/tests/protocol_context_actions_b.test.js`
  the same for the client validator. Run
  `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_view web.webclient.presentation.tests.test_combat_panel`
  and `node --test web/static/webclient/js/tests/protocol_context_actions_b.test.js web/static/webclient/js/tests/combat_menu.test.js web/static/webclient/js/tests/hud_dock_menus.test.js`,
  and verify both pass.

## 2. Client predicate and flow (≈2.5 h)

- [ ] 2.1 Create `web/webclient-app/stores/elosern/cross_side.js` (design D3) with the target-set expansion for
  SINGLE, SELF, AREA explicit and the three shorthands.
- [ ] 2.2 `stores/elosern/frames.js`: intercept the `target-*`, `self-confirm` and `area-confirm` submissions
  (design D4); add `confirmCrossSide` / `cancelCrossSide` and the invalidation on a `context_actions` replacement,
  playback lock and mode change. `stores/elosern/view.js`: publish `crossSideConfirm`. `stores/elosern/interaction.js`:
  claim no dock key while it is set.
- [ ] 2.3 `components/QuestionCard.vue`: `initialFocus` prop (`"yes"` default). `AppClient.vue`: the combat
  `QuestionCard` in the `choices` slot with `initial-focus="no"`, `inert` on the dock while it shows (design D5).
  `components/ActionDock.vue`: no change beyond accepting `inert` if the attribute is passed through.
- [ ] 2.4 Add `web/webclient-app/tests/store/cross_side_confirm.test.js`: the predicate over fixed inputs (harm →
  ally / self / foe / mixed AREA / `all` / `all-enemies`; restore → foe / ally / `all-allies`; both facts on foe,
  ally, `all`; neither fact; NONE → null) with the exact question strings; the flow (Enter, digit and
  `stageTargetPointer` activation on an ally with Attack send nothing and set `crossSideConfirm`; `confirmCrossSide`
  sends exactly one payload equal to the no-question payload; `cancelCrossSide` restores the focus key and leaves the
  AREA selection; Enter/arrows/digits with the question open dispatch nothing and move nothing; a panel replacement,
  `beatLocked` and a mode change clear it; Attack on a foe and heal on an ally dispatch at once). Add
  `web/webclient-app/tests/core/question_card.test.js`: `initialFocus="no"` focuses 否 on mount and after a lock
  releases; the default still focuses 是. Run
  `pnpm test -- web/webclient-app/tests/store/cross_side_confirm.test.js web/webclient-app/tests/core/question_card.test.js web/webclient-app/tests/store/stage_target_step.test.js web/webclient-app/tests/app_client_room_actions.test.js`
  and verify it passes (the last file guards the room cards' question).

## 3. Browser verification (≈1 h)

Build once: `pnpm run build`.

- [ ] 3.1 Add `test_cross_side_cast_asks_first` to `web/tests/browser/test_browser_combat_stage.py`
  `CombatStageBrowserTest`: Attack → a companion → Enter opens `[data-testid="cross-side-question"]` with role
  `dialog`, the text `確定要對友方使用〈基本攻擊〉？` and focus on 否, no `combat.cast` sent, every figure's
  `data-speaking` unchanged from the step; Escape returns to the step with focus on `#action-dock` and the same
  marker focused; Enter again then 是 sends exactly one `combat.cast` with that companion's `target_ids`; Attack on a
  foe sends at once with no dialog. Annotate it with the IDs it establishes (confirm spellings with `list`) and
  register it in `.github/browser-shards.json` beside the other `CombatStageBrowserTest` methods. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_cross_side_cast_asks_first web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_targets_are_picked_on_the_stage`
  and verify both pass.

## 4. Storybook (≈0.75 h)

- [ ] 4.1 Add the fixtures and stories of design D6. Run `pnpm run build-storybook` then
  `pnpm run showcase-coverage` and verify both succeed with `component-manifest.json` unchanged.

## 5. Documentation and gates (≈0.5 h)

- [ ] 5.1 Document `harms`/`restores` where the combat panel fields are described for developers (grep
  `docs/` for `freeform_scales` and add beside it) and the cross-side question in `web/webclient-app/AGENTS.md`'s
  combat section.
- [ ] 5.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`,
  `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract`,
  and `openspec validate webclient-combat-cross-side-confirm --strict`. Verify all pass.

## Workflow follow-up

- At archive, add the new ID of "A cast across sides asks for confirmation first" to
  `test_cross_side_cast_asks_first` and the modified descriptor scenario's ID stays on its existing tests.
