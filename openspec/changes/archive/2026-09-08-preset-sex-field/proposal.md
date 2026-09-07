## Why

Every character created from a shipped preset is persisted with `sex = "other"`.
The `sex` channel is collected only on the custom path; a preset request never
carries one (`commands/character_creation.py` builds
`CharacterCreationRequest(mode="preset", preset_key=...)`, and
`creation_wizard._request_from_draft` does the same for a saved preset draft),
so `character_creation.py`'s `_validate_sex(None)` normalizes the absent value to
`DEFAULT_SEX`. All eight shipped presets are authored as women — their
`background` prose and every `affinity.yaml` stage `look_flavor` use 她 — so the
persisted value contradicts the authored identity for the entire roster, and
that value feeds the sexual-state model, dialogue prompts, and namegen.

`PlayerPreset` predates the `world/lore/sex.py` vocabulary module and simply has
no field for it. This change closes that gap.

## What Changes

- `PlayerPreset` gains a **required** `sex` field, a `SEX_VALUES` member.
- `PlayerPreset` adopts `dataclasses.KW_ONLY` from `sex` onward, so `sex` is a
  required keyword argument. A new card that omits it fails at construction
  instead of silently inheriting `DEFAULT_SEX` — the exact defect this change
  closes. Existing positional arguments on the eight cards are unaffected.
- A new load-time validator `_validate_preset_sex` rejects any preset whose
  `sex` is not a `SEX_VALUES` member, joining the four validators that already
  run at `world/lore/player_presets.py` import.
- `preflight_character_creation` resolves `sex` in the same mode branch that
  resolves name/age/race: preset mode takes `preset.sex`, custom mode keeps
  `request.sex`. Both still flow through `_validate_sex` before persistence.
- All eight shipped cards declare `sex="female"`.
- `world/lore/sex.py`'s docstring names `PlayerPreset.sex` as a third consumer.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: a new requirement making the preset registry the
  source of a preset-created character's persisted sex, with load-time
  validation and the required-keyword construction rule.
- `entity-sex-vocabulary`: the requirement that `world/lore/sex.py` documents
  its consumers now must name `PlayerPreset.sex` alongside
  `CHARACTER_SCHEMA_V1` and `LivingEntity.sex`.

## Impact

- `world/lore/player_presets.py` — `PlayerPreset` field set, `KW_ONLY` marker,
  new validator, eight card literals.
- `world/rules/character_creation.py` — the preset branch of
  `preflight_character_creation` only. `activate_player_character` is unchanged:
  it already persists `validated.sex`.
- `world/lore/sex.py` — docstring only.
- `world/lore/tests/test_player_presets.py`,
  `world/rules/tests/test_character_creation.py` — new coverage.
- Unaffected: custom creation, the WebClient creation actions and their exact
  payload schemas, the Telnet wizard, the import path, and
  `tests/test_creation_parity_contract.py::test_sex_values_and_default_mirror_across_python_and_js`
  (this change adds a preset field and never touches `SEX_VALUES` or
  `DEFAULT_SEX`).
