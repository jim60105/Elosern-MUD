# player-character-creation delta

## ADDED Requirements

### Requirement: Preset activation persists the preset's declared sex
Every `PlayerPreset` SHALL declare a `sex` field holding exactly one
`SEX_VALUES` member, and preset-mode activation SHALL persist that value as the
activated character's `sex`. `preflight_character_creation` SHALL resolve the
value in the same mode branch that resolves the display name, ages, race, and
subrace: preset mode takes `preset.sex` and custom mode keeps `request.sex`,
with both branches still normalized through the single `_validate_sex`
validator before persistence. A preset-mode request SHALL NOT fall back to
`DEFAULT_SEX`.

`sex` SHALL be a required keyword argument of `PlayerPreset` (the dataclass
declares `dataclasses.KW_ONLY` from this field onward), so a card that omits it
fails at construction rather than silently inheriting the default. A preset
declaring a value outside `SEX_VALUES` SHALL fail at registry load, never at
player activation, matching the existing skill-kit, identity, affinity, and
starting-item validators.

Custom creation, the WebClient creation action payload schemas, the Telnet
wizard, and the import path are unchanged.

#### Scenario: A preset activation persists the preset's declared sex
- **WHEN** a pending player activates a shipped preset declaring `sex="female"`
- **THEN** the activated character's `sex` is `"female"`, written atomically with the rest of the activation state

#### Scenario: A preset request never falls back to the vocabulary default
- **WHEN** a preset-mode `CharacterCreationRequest` is built without a `sex` field, as every preset entry point does
- **THEN** the resolved sex is the preset's declared value and is not `DEFAULT_SEX` unless the preset itself declares `"other"`

#### Scenario: Custom activation still uses the request's sex
- **WHEN** a pending player activates a custom draft carrying a `SEX_VALUES` member
- **THEN** the activated character's `sex` equals that value, and a custom draft with a null sex still normalizes to `DEFAULT_SEX`

#### Scenario: A preset with an out-of-vocabulary sex is rejected at load
- **WHEN** a preset declares a `sex` that is not a `SEX_VALUES` member
- **THEN** importing `world.lore.player_presets` raises, so the invalid value can never reach a player's activation

#### Scenario: A preset omitting sex fails at construction
- **WHEN** a `PlayerPreset` is constructed without the `sex` keyword argument
- **THEN** construction raises `TypeError`, so a new card cannot silently inherit `DEFAULT_SEX`

#### Scenario: Every shipped preset declares a concrete sex
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** every entry declares a `SEX_VALUES` member, and the eight shipped cards all declare `"female"`

## MODIFIED Requirements

### Requirement: Character creation enforces canonical identity and registry compatibility
Both preset and custom activation SHALL require `age` and `apparent_age` to be independent integer values within the 0..10000 reasonable range. The selected race SHALL exist in `RACE_REGISTRY`. A subrace SHALL exist in `SUBRACE_REGISTRY` and belong to that race; in custom mode the subrace is required (every race has at least one registered subrace), while preset mode uses the preset's declared subrace. In custom mode a supplied sex SHALL be a `SEX_VALUES` member or omitted/null, the latter normalizing to `DEFAULT_SEX`; in preset mode the sex comes from the preset's own declared `sex` field and SHALL NOT fall back to `DEFAULT_SEX`. Successful activation SHALL persist the accepted age, apparent age, race, subrace, display name, and sex on the player character (the sex written as the `entity.sex` attribute the character loader already honors, so creation and import paths converge on the same concrete value).

#### Scenario: Actual age below the range floor is rejected
- **WHEN** custom creation supplies `age=-1` with an in-range apparent age
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: Apparent age outside the range is rejected independently
- **WHEN** custom creation supplies an in-range actual age and `apparent_age=-1`
- **THEN** activation is rejected, the character remains pending, and no traits are written

#### Scenario: A subrace belonging to another race is rejected
- **WHEN** custom creation chooses a subrace whose registry `race_key` differs from the selected race
- **THEN** activation is rejected before persistence with an explanation of the mismatch

#### Scenario: A custom creation with no subrace is rejected
- **WHEN** custom creation supplies a race and valid canonical ages but no subrace
- **THEN** activation is rejected before persistence with an explanation, and the character remains pending

#### Scenario: An imported character without a subrace is rejected
- **WHEN** a character import record supplies a race but omits, blanks, or mis-assigns the subrace
- **THEN** the import rejects the record before any entity is created, since every race has at least one registered subrace and no imported character bypasses the mandatory-subrace contract

#### Scenario: Activation persists the accepted sex on the entity
- **WHEN** a custom character activates with `sex` set to a non-default `SEX_VALUES` member
- **THEN** the activated character's `entity.sex` holds exactly that member, and a rollback of the activation transaction restores the pending shell's prior sex state

#### Scenario: Preset activation carries the preset's declared sex
- **WHEN** a preset-mode activation succeeds
- **THEN** the activated character's `entity.sex` holds the preset's declared `sex`, and it is `DEFAULT_SEX` only when the preset itself declares `"other"`
