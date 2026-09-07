## 1. Persona dataclasses

- [x] 1.1 Add `PresetIdentity` (frozen; `public: str = ""`, `hidden: str = ""`, so every persona value is optional and defaults to empty per the delta spec) to `world/lore/player_presets.py`
- [x] 1.2 Add `PresetAppearance` (frozen; exactly the seven `_SUBKEY_ORDER` sub-keys `height`, `weight`, `measurement`, `style`, `overview`, `attire`, `feature`, each defaulting to `""`)
- [x] 1.3 Add `PresetPersona` (frozen; `identity`, `personality`, `life_story`, `habit`, `appearance`, `social_connection` as a tuple of pairs, `background`), every field defaulting to empty
- [x] 1.4 Implement `PresetPersona.to_record()` returning the `entity.db.persona` storage shape used by custom activation and `persona_edit`: all six `PERSONA_IMPORT_CARD_KEYS` always present (`""` for unauthored prose, `{}` for unauthored structured keys), `identity.hidden` omitted when empty, `background` included only when non-empty
- [x] 1.5 Cross-check the emitted sub-key names against `world/rules/persona.py`'s `_SUBKEY_ORDER` and `_SUBKEY_LABELS` so the record renders with the localized labels

## 2. PlayerPreset field set

- [x] 2.1 Add keyword-only `persona: PresetPersona = PresetPersona()` to `PlayerPreset`
- [x] 2.2 Remove the `background` field from `PlayerPreset`
- [x] 2.3 Convert the eight cards' trailing positional arguments (`active_skills`, `passive_skills`, `affinity_elements`) to keyword arguments, since removing the positional `background` slot shifts them
- [x] 2.4 Move each card's existing background prose into `persona=PresetPersona(background=...)`, byte-identical
- [x] 2.5 Confirm `world/lore/player_presets.py` still imports nothing from `world.rules`

## 3. Validation

- [x] 3.1 Write `_validate_preset_personas(registry)` rejecting a non-string prose value, a non-`PresetIdentity` identity, a non-`PresetAppearance` appearance, or a `social_connection` entry that is not a pair of strings; register it with the existing validators at module bottom
- [x] 3.2 Add a load-time sweep in `world/rules/character_creation.py` asserting every registered preset's persona prose is at most `MAX_PERSONA_FIELD_LENGTH`, raising with the offending preset key and field name
- [x] 3.3 Verify the sweep runs at module import (not lazily), so an over-long field fails server start the same way an invalid skill kit does

## 4. Card and screen sources

- [x] 4.1 Change `build_preset_cards()` in `world/rules/creation_wizard.py` to read `preset.persona.background`
- [x] 4.2 Change `creation_start_screen()` in `commands/character_creation.py` to read `preset.persona.background` — it reads `preset.background` directly today, and it renders the first screen every pending player sees (reused by `Account.at_post_login`), so missing it is an immediate `AttributeError`
- [x] 4.3 Grep the whole repository for remaining `preset.background` / `.background` reads against a `PlayerPreset` and confirm there is no third consumer
- [x] 4.4 Confirm `PresetCardView`'s field set, `_serialize_preset_card`, and the creation panel payload are untouched

## 5. Tests

- [x] 5.1 `world/lore/tests/test_player_presets.py`: the persona validator rejects each malformed shape
- [x] 5.2 `world/lore/tests/test_player_presets.py`: no shipped preset exposes a top-level `background` attribute, and every entry's `persona.background` is non-empty
- [x] 5.3 `world/rules/tests/test_persona.py`: `to_record()` on a full persona renders through `PersonaStore.flatten()`; on an all-empty persona it still carries exactly the six `PERSONA_IMPORT_CARD_KEYS` (empty values) and flattens to `None`; `public_view()` prunes `identity.hidden` while keeping `identity.public`
- [x] 5.4 `world/rules/tests/test_character_creation.py`: the registry sweep raises for a persona prose value over `MAX_PERSONA_FIELD_LENGTH`
- [x] 5.5 `world/rules/tests/test_creation_wizard.py`: `build_preset_cards()` output is unchanged in field set and background text
- [x] 5.6 `commands/tests/test_character_creation.py`: update the two existing assertions that read `preset.background` (in `test_status_and_preset_activation` and `test_creation_start_screen_is_registry_derived_and_reusable`) to `preset.persona.background`, keeping their `covers_requirement` annotations intact
- [x] 5.7 `tests/test_creation_parity_contract.py`: every shipped preset's `persona.background` is at most `MAX_BACKGROUND_CODE_POINTS` (256), the WebClient preset-card descriptor bound
- [x] 5.8 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets world.rules.tests.test_persona world.rules.tests.test_creation_wizard world.rules.tests.test_character_creation commands.tests.test_character_creation`
- [x] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_creation_parity_contract`
- [x] 6.3 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient` for the creation panel serializer
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.5 `openspec validate preset-persona-model --strict`
