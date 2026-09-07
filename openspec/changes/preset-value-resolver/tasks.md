## 1. Extraction

- [ ] 1.1 Add a pure `resolve_preset_values(preset)` to `world/rules/character_creation.py` that resolves the starting profile, adds the preset's allocations to each axis lower bound, applies the subrace static modifiers with the existing `round(value * (1 + modifier))` behavior, and pins `guild_merit` to 0
- [ ] 1.2 Take only a `PlayerPreset`: no account, no character, no database read, no clock read, no write
- [ ] 1.3 Replace the inlined computation in `preflight_character_creation`'s preset branch with a call to it
- [ ] 1.4 Leave the custom branch's computation path behaving identically, whether or not it shares the helper
- [ ] 1.5 Confirm no other behavior, message, or validation order changes

## 2. Tests

- [ ] 2.1 `world/rules/tests/test_character_creation.py`: for every shipped preset, `resolve_preset_values(preset)` equals the trait values a full activation persists, axis for axis
- [ ] 2.2 `world/rules/tests/test_character_creation.py`: the resolver is callable with only a preset and performs no write
- [ ] 2.3 Run the existing creation test suite **unedited** as the regression net — any required edit means the extraction changed behavior and must be reworked
- [ ] 2.4 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 3. Verification

- [ ] 3.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation world.rules.tests.test_creation_wizard commands.tests.test_character_creation`
- [ ] 3.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_creation_actions`
- [ ] 3.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 3.4 `openspec validate preset-value-resolver --strict`
