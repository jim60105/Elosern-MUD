## 1. Lore data model

- [x] 1.1 Add `from dataclasses import KW_ONLY` and a `_: KW_ONLY` marker to `PlayerPreset` in `world/lore/player_presets.py`, placed after the existing fields so every current positional argument still binds unchanged
- [x] 1.2 Declare `sex: str` immediately after the `KW_ONLY` marker with no default, making it a required keyword argument
- [x] 1.3 Write `_validate_preset_sex(registry)` rejecting any preset whose `sex` is not a `SEX_VALUES` member, following the message style of `_validate_preset_identities`, and register the call alongside the four existing validators at module bottom
- [x] 1.4 Import `SEX_VALUES` from `world.lore.sex` (lore-to-lore only; `player_presets` must keep importing nothing from `world.rules`)

## 2. Shipped cards

- [x] 2.1 Add `sex="female"` to all eight entries of `PLAYER_PRESET_REGISTRY` (`human_wanderer`, `foxkin_scout`, `elf_guardian`, `violet_altoria`, `lidzia_rosenthal`, `yuka_darknight`, `yuna_darknight`, `elosia_shadowmoon`)
- [x] 2.2 Confirm `uv run --locked python -c "import world.lore.player_presets"` loads clean

## 3. Creation preflight

- [x] 3.1 In `preflight_character_creation`, resolve `sex` inside the existing mode branch: the preset branch takes `preset.sex`, the custom branch takes `request.sex`
- [x] 3.2 Replace the unconditional `checked_sex = _validate_sex(request.sex)` with `_validate_sex(<branch-resolved value>)`, keeping `_validate_sex` as the single normalizer for both modes
- [x] 3.3 Verify `activate_player_character` needs no edit — it already persists `validated.sex`

## 4. Vocabulary docstring

- [x] 4.1 Update `world/lore/sex.py`'s module docstring to name `PlayerPreset.sex` as a third consumer alongside `CHARACTER_SCHEMA_V1` and `LivingEntity.sex`

## 5. Tests

- [x] 5.1 `world/lore/tests/test_player_presets.py`: assert `_validate_preset_sex` rejects an out-of-vocabulary value
- [x] 5.2 `world/lore/tests/test_player_presets.py`: assert constructing a `PlayerPreset` without the `sex` keyword raises `TypeError`
- [x] 5.3 `world/lore/tests/test_player_presets.py`: assert every shipped card declares a `SEX_VALUES` member and that all eight declare `"female"`
- [x] 5.4 `world/rules/tests/test_character_creation.py`: assert a preset activation persists the preset's declared sex and never `DEFAULT_SEX`
- [x] 5.5 `world/rules/tests/test_character_creation.py`: assert custom activation still resolves the request's sex, and a null custom sex still normalizes to `DEFAULT_SEX`
- [x] 5.6 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list` (never hand-constructed)

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets world.rules.tests.test_character_creation`
- [x] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_creation_parity_contract` stays green (`SEX_VALUES`/`DEFAULT_SEX` untouched)
- [x] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.4 `openspec validate preset-sex-field --strict`
