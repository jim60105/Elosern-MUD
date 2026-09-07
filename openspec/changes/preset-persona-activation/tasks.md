## 1. Shared record builder

- [ ] 1.1 Extract the two existing persona branches of `activate_player_character` into `_persona_record_for(validated, request, persona)` in `world/rules/character_creation.py`, returning the record dict or `None`
- [ ] 1.2 Confirm the custom-mode return value is byte-identical to today's output for all three custom shapes (persona block present, background only, neither)
- [ ] 1.3 Add the preset branch returning `PLAYER_PRESET_REGISTRY[request.preset_key].persona.to_record()`
- [ ] 1.4 Call the helper from the single existing persona write site, keeping the write inside the activation `transaction.atomic()` block

## 2. Rollback surface

- [ ] 2.1 Verify `persona` is already a member of `_CREATION_ATTRIBUTE_KEYS`, so `snapshot_attributes`/`restore_attributes` already cover the preset path with no widening
- [ ] 2.2 Verify no other activation write ordering changes — the persona write keeps its current position relative to the portrait finalization and the draft clear

## 3. Tests

- [ ] 3.1 `world/rules/tests/test_character_creation.py`: a preset activation writes `entity.db.persona` equal to that preset's `to_record()` output
- [ ] 3.2 `world/rules/tests/test_character_creation.py`: a preset record and a custom record carry the same six `PERSONA_IMPORT_CARD_KEYS`
- [ ] 3.3 `world/rules/tests/test_character_creation.py`: an injected persona-write failure during a preset activation rolls back identity, traits, skills, inventory, and persona, leaving the character pending
- [ ] 3.4 `world/rules/tests/test_character_creation.py`: the three custom shapes still produce their pre-change records (regression guard on the extraction)
- [ ] 3.5 `typeclasses/tests/test_npc_dialogue.py`: an NPC dialogue context for a preset-created character resolves a non-empty player persona block
- [ ] 3.6 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [ ] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation typeclasses.tests.test_npc_dialogue`
- [ ] 4.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_persona_edit` if present, confirming `persona_edit` still behaves on a preset-created record
- [ ] 4.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 4.4 `openspec validate preset-persona-activation --strict`
