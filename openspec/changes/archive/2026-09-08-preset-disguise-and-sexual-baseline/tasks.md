## 1. Sexual baseline dataclass

- [x] 1.1 Add frozen `PresetSexualBaseline` to `world/lore/player_presets.py` with required `arousal`, `virgin`, `sensitivity` (tuple of body-part/level pairs) and optional `wetness`, `shame`, `exposure`, `climax_phase` defaulting to `""`
- [x] 1.2 Implement `to_record()` producing the `entity.db.sexual` storage shape, omitting every optional field left empty so `SexualState`'s existing "default the omitted field to its vocabulary's lowest level" rule applies unchanged
- [x] 1.3 Import the vocabulary tuples and `BODY_PARTS`/`GENERIC_BODY_PART` from `world/lore/sexual_vocab.py` (lore-to-lore only)

## 2. Registry fields

- [x] 2.1 Add keyword-only `disguised_stats: tuple[tuple[str, int], ...] = ()` to `PlayerPreset`
- [x] 2.2 Add keyword-only `sexual_baseline: PresetSexualBaseline | None = None` to `PlayerPreset`
- [x] 2.3 Write `_validate_preset_disguised_stats(registry)` requiring string keys and exact `int` values (rejecting booleans), with no axis whitelist
- [x] 2.4 Write `_validate_preset_sexual_baselines(registry)` checking each declared level against its vocabulary tuple and each `sensitivity` key against `BODY_PARTS` plus `GENERIC_BODY_PART`
- [x] 2.5 Register both validators with the existing validators at module bottom

## 3. Activation

- [x] 3.1 Add `"disguised_stats"` and `"sexual"` to `_CREATION_ATTRIBUTE_KEYS`
- [x] 3.2 Write `"disguised_stats": dict(preset.disguised_stats) or None` into the activation attribute map, mirroring `world/imports/loader.py`'s normalization
- [x] 3.3 Write `"sexual": preset.sexual_baseline.to_record()` only when the preset declares a baseline; omit the key entirely otherwise so the attribute stays absent
- [x] 3.4 Confirm custom mode writes neither key, preserving today's behavior

## 4. Boundary documentation

- [x] 4.1 Update `get_display_value`'s docstring to state that the reader set is unchanged and that `world/imports/loader.py` and `world/rules/character_creation.py` are the two sanctioned writers of the layer
- [x] 4.2 Confirm `world/rules/tests/test_disguise_boundary.py`'s `FORBIDDEN_MODULES` list still passes untouched

## 5. Tests

- [x] 5.1 `world/lore/tests/test_player_presets.py`: the disguise validator rejects a non-string key, a non-integer value, and a boolean value
- [x] 5.2 `world/lore/tests/test_player_presets.py`: the baseline validator rejects an out-of-vocabulary level and an unknown sensitivity body part
- [x] 5.3 `world/rules/tests/test_character_creation.py`: a declared disguise layer is persisted and the character's true traits are unchanged
- [x] 5.4 `world/rules/tests/test_character_creation.py`: an empty disguise declaration writes `None`
- [x] 5.5 `world/rules/tests/test_character_creation.py`: a declared baseline reaches `entity.sexual`, and a `None` baseline leaves `db.sexual` absent with the generic default applied
- [x] 5.6 `world/rules/tests/test_character_creation.py`: a failure injected after both writes restores `disguised_stats` and `sexual` in the in-process cache
- [x] 5.7 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets world.rules.tests.test_character_creation world.rules.tests.test_disguise_boundary`
- [x] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_sexual_state`
- [x] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.4 `openspec validate preset-disguise-and-sexual-baseline --strict`
