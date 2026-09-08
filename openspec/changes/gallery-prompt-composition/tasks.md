## 1. Prompt library

- [ ] 1.1 Add `{equipment}` and `{custom}` slots to `art.character_description` in `prompts/art.yaml`, phrased so an empty value leaves a clean sentence (mirroring the existing `{appearance}` slot)
- [ ] 1.2 Extend the `art.character_description` `PromptSpec` `allowed_placeholders` in `world/prompts/registry.py` with `equipment` and `custom`
- [ ] 1.3 Confirm the project's prompt validation entry point accepts the updated template and that placeholder set equality still holds

## 2. Field catalog and fragments

- [ ] 2.1 Create `world/art/gallery_prompt.py` with the closed ordered catalog `("appearance", "weapon_main", "weapon_off", "armor", "accessories")` and `validate_fields(...)` rejecting unknown, non-string, and duplicated ids and normalizing to declared order
- [ ] 2.2 Add `equipment_fragment(entity, fields)`: read stored slot values through the gallery snapshot reader, look up `ITEM_REGISTRY` presentations read-only, sort accessories by item key, skip empty slots and unregistered keys, never raise
- [ ] 2.3 Add `validate_custom_prompt(text)`: type check, declared code-point bound, control-character rejection (line/paragraph separators included), whitespace normalization to one line
- [ ] 2.4 Keep the module free of `world.ai`, `ollama`, `llm_client`, and `world.art.connectivity` imports and free of every write to entity state

## 3. Description composition

- [ ] 3.1 Make `world/art/subjects.py::character_description` selection-aware: contribute the appearance block only when `appearance` is selected
- [ ] 3.2 Pass the equipment fragment and the validated free text into `render_prompt("art.character_description", ...)` as `equipment` and `custom`
- [ ] 3.3 Keep every existing exclusion: no other persona key, neither identity layer, no secret state, no combat resource, no disguised stat
- [ ] 3.4 Leave the `PromptUnavailableError` fallback registry-driven with no persona, equipment, or free-text read
- [ ] 3.5 Update the existing deterministic seams — including the gallery request in `world/art/service.py` that `gallery-autogen-retrofit` already rewrote — to select `appearance` explicitly, so their descriptions are unchanged
- [ ] 3.6 Skim `world/lore/items.py` for `summary_zh` values that describe mechanics or taste rather than appearance, and record any that read poorly as prompt text (the field is a player-facing blurb, not an authored visual-appearance field); fix nothing in this change

## 4. Service seam

- [ ] 4.1 Add `fields=()` and `custom_prompt=""` to `request_gallery_image`, validating both before any subject derivation side effect and before any queue write
- [ ] 4.2 Store the normalized selection on the pending job so the settled card's `requested_fields` carries it verbatim
- [ ] 4.3 Raise typed service-boundary errors for every rejection, leaving no record, prompt, or card behind

## 5. Tests

- [ ] 5.1 `world/art/tests/`: selection normalization, `requested_fields` on the settled card, unknown/duplicate/non-string id rejection, empty selection accepted
- [ ] 5.2 `world/art/tests/`: an unselected `appearance` reproduces the pre-appearance description byte-for-byte
- [ ] 5.3 `world/art/tests/`: selected equipment fields contain the registry presentation text and no mechanics, stat, price, or rarity data
- [ ] 5.4 `world/art/tests/`: accessories sorted by key; empty slot, unregistered key, and malformed storage contribute nothing without raising; no equipment state is written
- [ ] 5.5 `world/art/tests/`: free text appended verbatim; over-long and control-bearing text rejected before any render; empty text a legal no-op
- [ ] 5.6 `world/art/tests/`: the same entity, selection, and free text produce byte-identical output twice
- [ ] 5.7 `world/art/tests/`: the broken-library fallback reads no persona, equipment, or free text
- [ ] 5.8 `world/prompts/tests/`: the placeholder set for `art.character_description` matches the template's slots
- [ ] 5.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art world.prompts`
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check`
- [ ] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 6.4 `openspec validate gallery-prompt-composition --strict`
