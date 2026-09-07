## 1. Shared record builder

- [x] 1.1 Extract the two existing persona branches of `activate_player_character` into `_persona_record_for(validated, request, persona)` in `world/rules/character_creation.py`, returning the record dict or `None`
- [x] 1.2 Confirm the custom-mode return value is byte-identical to today's output for all three custom shapes (persona block present, background only, neither)
- [x] 1.3 Add the preset branch returning `PLAYER_PRESET_REGISTRY[request.preset_key].persona.to_record()`
- [x] 1.4 Call the helper from the single existing persona write site, keeping the write inside the activation `transaction.atomic()` block

## 2. Rollback surface

- [x] 2.1 Verify `persona` is already a member of `_CREATION_ATTRIBUTE_KEYS`, so `snapshot_attributes`/`restore_attributes` already cover the preset path with no widening
- [x] 2.2 Verify no other activation write ordering changes — the persona write keeps its current position relative to the portrait finalization and the draft clear

## 3. Tests

- [x] 3.1 `world/rules/tests/test_character_creation.py`: a preset activation writes `entity.db.persona` equal to that preset's `to_record()` output
- [x] 3.2 `world/rules/tests/test_character_creation.py`: a preset record and a custom record carry the same six `PERSONA_IMPORT_CARD_KEYS`
- [x] 3.3 `world/rules/tests/test_character_creation.py`: an injected persona-write failure during a preset activation rolls back identity, traits, skills, inventory, and persona, leaving the character pending
- [x] 3.4 Custom-shape regression rides the existing end-to-end pins (`test_concept_persona_persists_in_the_six_key_import_card_shape`, `test_draft_without_persona_writes_nothing`, `test_custom_background_is_persisted_inside_the_persona_record`, `test_background_merges_with_a_concept_persona_block`); add one helper-level test for the preset-mode-plus-persona-arg precedence edge
- [x] 3.5 `typeclasses/tests/test_npc_dialogue.py`: an NPC dialogue context for a preset-created character whose persona declares dialogue-visible fields (registry entry patched via `patch.dict` + `dataclasses.replace`, since every shipped card is background-only) resolves a non-empty player persona block; plus a companion test that a shipped background-only card's character gets the record but no dialogue block (policy documentation)
- [x] 3.6 Annotate the tests with `covers_requirement`: the stable `creation-persona-persistence::...` ID from day one; the new `player-character-creation::...` ID lands in the SAME commit as the archive-phase spec sync (`check`/`verify` only index `openspec/specs/`)

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation world.rules.tests.test_creation_wizard typeclasses.tests.test_npc_dialogue`
- [x] 4.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_persona_edit`, confirming `persona_edit` still behaves on a preset-created record
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 4.4 `openspec validate preset-persona-activation --strict`
