## 1. Prompt library

- [x] 1.1 Add `{equipment}` and `{custom}` slots to `art.character_description` in `prompts/art.yaml`, phrased so an empty value leaves a clean sentence (mirroring the existing `{appearance}` slot)
- [x] 1.2 Extend the `art.character_description` `PromptSpec` `allowed_placeholders` in `world/prompts/registry.py` with `equipment` and `custom`
- [x] 1.3 Confirm the project's prompt validation entry point accepts the updated template and that placeholder set equality still holds

## 2. Field catalog and fragments

- [x] 2.1 Create `world/art/gallery_prompt.py` with the closed ordered catalog `("appearance", "weapon_main", "weapon_off", "armor", "accessories")` and `validate_fields(...)` rejecting unknown, non-string, and duplicated ids and normalizing to declared order
- [x] 2.2 Add `equipment_fragment(entity, fields)`: read stored slot values through the gallery snapshot reader, look up `ITEM_REGISTRY` presentations read-only, sort accessories by item key, skip empty slots and unregistered keys, never raise
- [x] 2.3 Add `validate_custom_prompt(text)`: type check, declared code-point bound, control-character rejection (line/paragraph separators included), whitespace normalization to one line
- [x] 2.4 Keep the module free of `world.ai`, `ollama`, `llm_client`, and `world.art.connectivity` imports and free of every write to entity state

## 3. Description composition

- [x] 3.1 Make `world/art/subjects.py::character_description` selection-aware: contribute the appearance block only when `appearance` is selected
- [x] 3.2 Pass the equipment fragment and the validated free text into `render_prompt("art.character_description", ...)` as `equipment` and `custom`
- [x] 3.3 Keep every existing exclusion: no other persona key, neither identity layer, no secret state, no combat resource, no disguised stat
- [x] 3.4 Leave the `PromptUnavailableError` fallback registry-driven with no persona, equipment, or free-text read
- [x] 3.5 Update the existing deterministic seams — including the gallery request in `world/art/service.py` that `gallery-autogen-retrofit` already rewrote — to select `appearance` explicitly, so their descriptions are unchanged
- [x] 3.6 Skim `world/lore/items.py` for `summary_zh` values that describe mechanics or taste rather than appearance, and record any that read poorly as prompt text (the field is a player-facing blurb, not an authored visual-appearance field); fix nothing in this change.
  Recorded (mechanic/taste clauses that read poorly as visual prompt text; equipment slots only, cosmetics otherwise fine): `apotarchary` — `apothecary_beads` "溫潤的氣息緩緩滋養身體" (nourish-mechanic), `archmage_mending_robe` "施法時法力的耗損明顯減輕" (pure mechanic), `enticing_lace_set` "穿者舉手投足自帶挑逗的氣息" (taste/aura), `passion_silk_choker` "肌膚愈親近，感官愈熾熱" (arousal mechanic), `fearless_brooch` "佩戴者無視恐懼的低語" (fear-immunity mechanic), `purified_pendant` "據說能隔絕瘴毒" (legend-mechanic), `knight_platemail` "防護全面但極為沉重" (weight/protection stat), `sister_vestments` / `radiant_holy_emblem` / `saintess_vestments` (healing/holy-effect clauses), `storage_pouch` "帝國壟斷的空間魔法小袋" (property, not visual).

## 4. Service seam

- [x] 4.1 Add `fields=()` and `custom_prompt=""` to `request_gallery_image`, validating both before any subject derivation side effect and before any queue write
- [x] 4.2 Store the normalized selection on the pending job so the settled card's `requested_fields` carries it verbatim
- [x] 4.3 Raise typed service-boundary errors for every rejection, leaving no record, prompt, or card behind

## 5. Tests

- [x] 5.1 `world/art/tests/`: selection normalization, `requested_fields` on the settled card, unknown/duplicate/non-string id rejection, empty selection accepted
- [x] 5.2 `world/art/tests/`: an unselected `appearance` reproduces the pre-appearance description byte-for-byte
- [x] 5.3 `world/art/tests/`: selected equipment fields contain the registry presentation text and no mechanics, stat, price, or rarity data
- [x] 5.4 `world/art/tests/`: accessories sorted by key; empty slot, unregistered key, and malformed storage contribute nothing without raising; no equipment state is written
- [x] 5.5 `world/art/tests/`: free text appended verbatim; over-long and control-bearing text rejected before any render; empty text a legal no-op
- [x] 5.6 `world/art/tests/`: the same entity, selection, and free text produce byte-identical output twice
- [x] 5.7 `world/art/tests/`: the broken-library fallback reads no persona, equipment, or free text
- [x] 5.8 `world/prompts/tests/`: the placeholder set for `art.character_description` matches the template's slots
- [x] 5.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art world.prompts`
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check`
- [ ] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 6.4 `openspec validate gallery-prompt-composition --strict`
