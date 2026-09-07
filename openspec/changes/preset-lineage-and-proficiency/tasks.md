## 1. Registry field

- [ ] 1.1 Add keyword-only `skill_proficiency: tuple[tuple[str, float], ...] = ()` to `PlayerPreset`
- [ ] 1.2 Write `_validate_preset_skill_proficiency(registry)` rejecting a key absent from `SKILL_REGISTRY`, a repeated key, a boolean, a non-numeric value, or a negative value; register it with the existing validators at module bottom
- [ ] 1.3 Mirror the import validator's message style so a bad entry names the preset and the offending key

## 2. Activation

- [ ] 2.1 In `activate_player_character`, replace the direct `preset.skill_lists()` write with a closed set: call `lineage_ownership_closure([*active, *passive])` from `world/rules/progression.py`
- [ ] 2.2 Append closure-added active keys after the declared active keys and closure-added passive keys after the declared passive keys, so the declared order is preserved
- [ ] 2.3 Call `seed_lineage_proficiency()` over the closed set, then apply the preset's declared `skill_proficiency` entries on top so a declared value always wins
- [ ] 2.4 Replace the hard-written `"skill_proficiency": {}` with the merged map; keep custom mode writing an empty map
- [ ] 2.5 Do not reuse `normalize_lineage_record` — it takes an import-record dict; compose the two public helpers directly

## 3. Tests

- [ ] 3.1 `world/lore/tests/test_player_presets.py`: the proficiency validator rejects an unknown key, a duplicate key, a negative value, and a non-numeric value
- [ ] 3.2 `world/rules/tests/test_character_creation.py`: a preset declaring a skill with an unsatisfied prerequisite activates with the closed chain owned and the prerequisite seeded to exactly the required value
- [ ] 3.3 `world/rules/tests/test_character_creation.py`: `can_use_skill` passes for every declared active key of every shipped preset after activation
- [ ] 3.4 `world/rules/tests/test_character_creation.py`: a declared `skill_proficiency` entry below the seed value survives activation unchanged
- [ ] 3.5 `world/rules/tests/test_character_creation.py`: declared keys keep their declared order and closure-added keys follow them
- [ ] 3.6 `world/rules/tests/test_character_creation.py`: custom activation still writes empty skill lists and an empty proficiency map
- [ ] 3.7 `world/rules/tests/test_progression.py`: the preset path and the import path produce the same seeded values for the same skill set
- [ ] 3.8 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [ ] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets world.rules.tests.test_character_creation world.rules.tests.test_progression`
- [ ] 4.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.imports` confirming the import path is untouched
- [ ] 4.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 4.4 `openspec validate preset-lineage-and-proficiency --strict`
