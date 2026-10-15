# Tasks

Testing rules as in root `AGENTS.md` "Testing": run focused commands only. Evennia commands use an env file
containing `MUD_TEST_SETTINGS=1`, passed as `--env-file=<file>`. Add no new Python test module, so
`.github/evennia-shards.json` stays unchanged.

## 1. Classification and view (≈2.5 h)

- [x] 1.1 Create `world/skills/effects/polarity.py` (design D3) with the table, reasons and `skill_target_polarity`.
- [x] 1.2 `world/rules/combat_view.py`: add `conditions` to `ParticipantView` (design D2) and `hostile`/`beneficial` to
  `SkillDescriptorView`; derive both while building participants and skills.
- [x] 1.3 Add tests in `world/rules/tests/test_combat_view.py`:
  - the ten skill cases of the delta scenario, using synthetic registry rows (in the module's existing style) where no
    shipped skill exists;
  - the exhaustiveness check;
  - participant conditions: a poisoned foe, a blessed companion, more than eight conditions cut to eight, an
    unmodelled entity giving `[]`, and the hidden-condition check of design D2;
  - a synthetic SELF skill with a `SELECTED` hostile effect reads `hostile: true`.

  Update the module's existing keyword constructions of `SkillDescriptorView`/`ParticipantView`. Run the Evennia
  focused labels `world.rules.tests.test_combat_view` and `world.skills.tests` and verify they pass.

## 2. Wire v6 (≈2.5 h)

- [ ] 2.1 Update the wire mirrors (design D4):
  - `web/webclient/presentation/combat_panel.py`: set `CONTEXT_ACTIONS_SCHEMA_VERSION = 6` and update the serializers
    and exact validators.
  - `web/static/webclient/js/elosern/protocol/constants.js`: set `context_actions: 6` and add the bound.
  - `protocol/panels/combat.js`: update the participant and skill validators.
  - `tests/test_panel_schema_version_parity_contract.py`: update its expectations if it pins the number.
- [ ] 2.2 Update the fixtures, preferring the shared builders. Find them with
  `grep -rln "\"shorthands\"\|shorthands:\|shorthands=\|portrait_ref" web/webclient/presentation/tests web/static/webclient/js/tests web/webclient-app/tests web/webclient-app/stories web/tests/browser world/rules/tests`.
  The grep is a starting point; the runs in 2.3 are the authority.
- [ ] 2.3 Run each of the following and verify it passes:
  - the Evennia focused labels `web.webclient.presentation.tests.test_combat_panel`,
    `web.webclient.presentation.tests.test_registry`, `tests.test_panel_schema_version_parity_contract` and
    `tests.test_context_actions_parity_contract`;
  - `node --test web/static/webclient/js/tests/protocol_context_actions_b.test.js web/static/webclient/js/tests/combat_menu.test.js web/static/webclient/js/tests/hud_dock_menus.test.js`;
  - `pnpm test -- web/webclient-app/tests/preserved_contract.test.js web/webclient-app/tests/store/combat_command_window.test.js web/webclient-app/tests/combat/participant_frame.test.js`;
  - the browser method that boots a real combat panel,
    `web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_attack_flow_submits_basic_attack_once`,
    through `web.tests.browser.unittest_driver`, with its output captured to a scratch file.

## 3. Traceability and gates (≈1 h)

- [ ] 3.1 At archive, after the sync, re-annotate the tests that carry the IDs of the three renamed requirements with
  the new IDs. List the IDs with `uv run --locked python -m tools.spec_traceability list --json-output <scratch>/ids.json`.
- [ ] 3.2 Run each of the following and verify it passes:
  - `uv run --locked python -m tools.spec_traceability check`;
  - `uv run --locked python -m tools.contract_gate`;
  - the Evennia focused labels `tests.test_evennia_test_optimization_contract` and
    `tests.test_webclient_frozen_contract`;
  - `openspec validate webclient-combat-panel-v6 --strict`.
