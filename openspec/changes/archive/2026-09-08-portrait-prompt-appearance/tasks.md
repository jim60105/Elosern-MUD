## 1. Prompt library

- [x] 1.1 Add an `{appearance}` slot to the `art.character_description` template in `prompts/art.yaml`, phrased so an empty value leaves a clean sentence
- [x] 1.2 Add `"appearance"` to the `allowed_placeholders` tuple of the `art.character_description` `PromptSpec` in `world/prompts/registry.py`
- [x] 1.3 Confirm `uv run --locked python -m world.prompts.validate` (or the project's prompt validation entry point) accepts the updated template

## 2. Description builder

- [x] 2.1 In `world/art/subjects.py::character_description`, read the entity's persona `appearance` block through `PersonaStore`
- [x] 2.2 Render the sub-keys in `world/rules/persona.py::_SUBKEY_ORDER` order, skipping empty values, into a single bounded fragment
- [x] 2.3 Pass the fragment into `render_prompt("art.character_description", …)` as `appearance`
- [x] 2.4 Read no other persona key; do not route through the full `flatten()` field set
- [x] 2.5 Leave the `PromptUnavailableError` fallback untouched, with no persona read

## 3. Tests

- [x] 3.1 `world/art/tests/`: a description for a fully authored character contains every appearance sub-key and no other persona text
- [x] 3.2 `world/art/tests/`: a character declaring `identity.hidden` produces a description containing neither identity layer
- [x] 3.3 `world/art/tests/`: two generations for the same character are byte-identical, with sub-keys in declared order
- [x] 3.4 `world/art/tests/`: a character with an empty appearance block produces the pre-change description
- [x] 3.5 `world/art/tests/`: a character with a disguise still shows no disguised stat as physical truth
- [x] 3.6 `world/art/tests/`: the degraded fallback reads no persona
- [x] 3.7 `world/prompts/tests/`: the placeholder set for `art.character_description` matches the template's slots
- [x] 3.8 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art world.prompts`
- [x] 4.2 `uv run --locked python -m tools.spec_traceability check`
- [x] 4.3 `openspec validate portrait-prompt-appearance --strict`
