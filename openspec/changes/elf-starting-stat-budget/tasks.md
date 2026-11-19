# Tasks

## 1. Creation policy and staging

- [ ] 1.1 In `world/rules/character_creation.py`, update `StartingProfile`, `resolve_starting_profile`, `_validate_allocations`, and `_resolve_values` to use the design's exact conversion. Update custom activation and `resolve_preset_values` to select their modes explicitly, and update every caller and allocation fixture to use point caps or the preset policy as appropriate. Leave companion and import resolution, lore rows, and combat unchanged.
- [ ] 1.2 In `world/rules/creation_wizard.py`, apply the marker in `save_custom_draft`, project the incomplete variant in `_normalize_draft`, and block it in `_request_from_draft`. Verify both `activate_draft` and the `creation.activate` adapter in `web/webclient/actions/creation_actions.py` reject the incomplete state before committing or touching portrait state. Keep the existing explicit reset behavior.
- [ ] 1.3 In `world/rules/tests/test_character_creation/` and `test_creation_wizard.py`, use synthetic bounds and cap inputs to cover both endpoints, a mixed exact-half tie, modifier order, invalid sums/keys/types/ranges, and unchanged modes. Cover stale direct confirmation, retained fields and portrait, valid resave followed by confirmation, and unaffected drafts in the draft and action suites.

## 2. Creation surfaces

- [ ] 2.1 Update `_axis_views` and `_profiles` in `world/rules/creation_wizard.py`, the registry-backed schema and validators in `web/webclient/presentation/creation.py`, and the mirrored `protocol/constants.js` and `protocol/panels/creation.js` under `web/static/webclient/js/elosern/`. Cut over fixtures and both validators to v9 together; reject v8, bad axis descriptors, and mismatched stage/allocation pairs.
- [ ] 2.2 Update `creation_menu.js` under the same static directory plus `web/webclient-app/composables/use-creation-form.js`, `use-creation-overlay.js`, and `components/CreationCustomSteps.vue` for point bounds, pre-modifier preview, incomplete draft hydration at allocation, and confirmation gating. Preserve identity, prose, and portrait. Test preview against the rules conversion and keep the seven-key save payload unchanged.
- [ ] 2.3 Update `CmdCharacter` in `commands/character_creation.py` to brief and collect points from the custom profile. Migrate `world/ai/character_creation.py::_validate_allocations` and `build_race_catalog` to that profile and verify WebClient proposal admission in `creation_actions.py` and Telnet continuation in `commands/character_creation.py`. Test a valid new-policy proposal through both and rejection of the old budget by the guard; keep non-elf proposal behavior unchanged.
- [ ] 2.4 Update the raw-increment explanation in `docs/development/adding-player-presets.md` to distinguish preset from custom elf policy. Record the test targets below as spec traceability and complete the design's named human review.

## Acceptance commands

Run from the repository root with the standard Evennia test env file configured per `docs/development/evennia-testing-guide.md`. Each test command must pass.

```sh
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb \
  world.rules.tests.test_character_creation world.rules.tests.test_creation_wizard \
  commands.tests.test_character_creation world.ai.tests.test_character_creation \
  web.webclient.actions.tests.test_creation_actions web.webclient.presentation.tests.test_creation_panel
node --test web/static/webclient/js/tests/{protocol_creation,creation_menu}.test.js
npm test -- web/webclient-app/tests/overlays/{creation_overlay,creation_steps}.test.js
openspec validate elf-starting-stat-budget --strict
```
