# player-character-creation delta

## ADDED Requirements

### Requirement: Preset activation persists the preset's declared disguise layer and sexual baseline
Every `PlayerPreset` MAY declare a keyword-only `disguised_stats` field, a tuple of
`(axis_key, value)` pairs, and a keyword-only `sexual_baseline` field holding either a frozen
`PresetSexualBaseline` or `None`. Both SHALL default to the empty form, and the empty form SHALL
preserve today's behavior exactly.

Preset activation SHALL write `entity.db.disguised_stats` as the declared mapping, or `None` when
the declaration is empty — the same normalization the import loader applies — inside the same
all-or-nothing activation transaction. Activation SHALL write `entity.db.sexual` from
`sexual_baseline.to_record()` only when the preset declares a baseline; when it declares `None`,
activation SHALL write nothing, so `SexualState` keeps applying its generic default lazily on first
construction.

`PresetSexualBaseline` SHALL mirror the import card's `sexual_baseline` object: `arousal`, `virgin`,
and `sensitivity` are required, and `wetness`, `shame`, `exposure`, and `climax_phase` are optional,
each omitted value defaulting through the existing `SexualState` construction rule rather than being
written as a literal.

`disguised_stats` and `sexual` SHALL join the activation attribute snapshot set, so a rolled-back
activation leaves no readable disguise or sexual-baseline residue in the in-process attribute cache.

A declaration SHALL fail at registry load, never at player activation, when a `disguised_stats` key
is not a string or its value is not an `int`, when a `sexual_baseline` level is not a member of its
vocabulary tuple in `world/lore/sexual_vocab.py`, or when a `sensitivity` key is not a member of
`BODY_PARTS` plus `GENERIC_BODY_PART`. `disguised_stats` keys SHALL NOT be restricted to a
whitelist: `CHARACTER_SCHEMA_V1` constrains the field only to integer values, and preset parity with
the import card is the point of the field.

#### Scenario: A declared disguise layer is persisted
- **WHEN** a pending player activates a preset declaring `disguised_stats`
- **THEN** `entity.db.disguised_stats` equals the declared mapping, written atomically with the rest of the activation state, and the character's true traits are unchanged

#### Scenario: An empty disguise declaration writes None
- **WHEN** a pending player activates a preset declaring no `disguised_stats`
- **THEN** `entity.db.disguised_stats` is `None`, which every existing reader already treats as absent

#### Scenario: A declared sexual baseline seeds the handler
- **WHEN** a pending player activates a preset declaring a `sexual_baseline`
- **THEN** `entity.db.sexual` equals the declared record and the constructed `entity.sexual` derives its fields from it rather than from the generic default

#### Scenario: An undeclared sexual baseline preserves the lazy default
- **WHEN** a pending player activates a preset declaring `sexual_baseline=None`
- **THEN** `entity.db.sexual` is absent and `SexualState` constructs from `_generic_default_baseline()` exactly as before this change

#### Scenario: A failed activation leaves no disguise or baseline residue
- **WHEN** a write failure is injected after the disguise and baseline writes of a preset activation
- **THEN** `disguised_stats` and `sexual` both read back at their pre-activation values and the character remains pending

#### Scenario: An invalid declaration is rejected at load
- **WHEN** a preset declares a non-string `disguised_stats` key, a non-integer value, a `sexual_baseline` level outside its vocabulary tuple, or a `sensitivity` key outside `BODY_PARTS` plus `GENERIC_BODY_PART`
- **THEN** importing `world.lore.player_presets` raises, so the invalid declaration can never reach a player's activation
