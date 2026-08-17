# Tasks: Raise the Combat-Panel Skill-Count Bound (MAX_SKILLS)

## 1. Raise the bound

- [ ] 1.1 Change `MAX_SKILLS = 32` to `MAX_SKILLS = 192` in `world/rules/combat_view.py`, updating
      the comment to state the rationale (154-skill theoretical maximum, multiple of 16).
- [ ] 1.2 Change `var MAX_SKILLS = 32;` to `var MAX_SKILLS = 192;` in
      `web/static/webclient/js/elosern/protocol.js`, keeping the mirror comment in sync.
- [ ] 1.3 Confirm `web/webclient/presentation/combat_panel.py` needs no edit beyond re-importing
      the raised constant (it imports `MAX_SKILLS` from `world.rules.combat_view`).

## 2. Boundary and capacity tests

- [ ] 2.1 Update `web/static/webclient/js/tests/protocol.test.js`: the flattened-count test rejects
      `193` skills and passes `192` (replace the hardcoded 33/32 boundary).
- [ ] 2.2 Update `web/webclient/presentation/tests/test_combat_panel.py`: the flattened-count test
      rejects `193` and passes `192`.
- [ ] 2.3 Add a catalog-complete capacity test (annotate with `covers_requirement`): an entity
      owning every currently obtainable active skill (all 91 base active skills plus all 63
      registered acts) builds the combat view without raising `CombatViewError`, and the serialized
      `context_actions` payload's canonical JSON size is at or below
      `MAX_CANONICAL_JSON_BYTES` (65,536). If the measured payload exceeds the limit, lower
      `MAX_SKILLS` to the largest multiple of 16 that fits, update tasks 1.1/1.2 and the boundary
      tests to match, and re-run this test — the raised value stands only when this gate passes.
- [ ] 2.4 Check `world/rules/tests/test_combat_view.py` for any `MAX_SKILLS` boundary assertion and
      update it to the new value.
- [ ] 2.5 Annotate the boundary tests with `covers_requirement` for the amended
      `webclient-combat-menu` requirement IDs.

## 3. Validation

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 3.2 Run the affected Evennia package tests (`world.rules.tests.test_combat_view`,
      `web.webclient.presentation.tests.test_combat_panel`) and the Node protocol tests
      (`node --test web/static/webclient/js/tests/protocol.test.js`).
- [ ] 3.3 Run `openspec validate --change combat-panel-skill-capacity --strict`.
- [ ] 3.4 Confirm `git diff --check` is clean.
