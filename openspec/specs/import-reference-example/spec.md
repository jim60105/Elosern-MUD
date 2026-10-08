# import-reference-example Specification

## Purpose
Maintains one valid reference character card that satisfies CHARACTER_SCHEMA_V1 and every semantic rule with zero rejections, exercised by a permanent test. Requires the example to exercise every major schema branch, a complete compact NPC card as its persona, and the base-value stats convention.

## Requirements

### Requirement: One valid reference character card exists and stays valid
`world/imports/examples/example_character.json` SHALL be a single character record with
`"record_type": "character"`, satisfying `CHARACTER_SCHEMA_V1` and every semantic validation rule
with zero rejections, with `age` and `apparent_age` inside the 0-10000 reasonable range. A permanent
test SHALL load this file and assert it produces zero rejections and zero warnings against the
current schema and lore registries.

#### Scenario: The reference example sets the required record_type discriminator
- **WHEN** `examples/example_character.json`'s `record_type` field is inspected
- **THEN** it is exactly `"character"`

#### Scenario: The reference example produces zero rejections
- **WHEN** `examples/example_character.json` is validated with `world.imports.validate`
- **THEN** the validation report contains zero rejections for this record

#### Scenario: The reference example produces zero warnings
- **WHEN** `examples/example_character.json` is validated with `world.imports.validate`
- **THEN** the validation report contains zero warnings for this record — its `stats` values fall
  inside its declared race's plausible band, and every `skills`/`passives` key either resolves
  against an available skill registry or is expected to warn only during the documented pre-change-5
  window

#### Scenario: The reference example carries plain in-range ages
- **WHEN** `examples/example_character.json`'s `age` and `apparent_age` are inspected
- **THEN** both are integers inside the 0-10000 reasonable range (the authored card carries 22),
  so the reference reads as an ordinary character record rather than an edge-case demonstration

### Requirement: The reference example carries a complete compact NPC card
`world/imports/examples/example_character.json`'s `persona` SHALL be a complete compact NPC card
written in Traditional Chinese — `identity` with `public` and `hidden`, `appearance`,
`personality`, `speech_style`, `life_story`, `habit`, and `social_connection` — that passes the
card contract as validated against the NPC default target with zero rejections and zero warnings,
and SHALL carry no `background` key.

#### Scenario: The reference persona is a valid compact card
- **WHEN** the example is validated with `world.imports.validate` against the NPC default
- **THEN** its persona passes the compact card contract and the report has zero rejections and zero warnings

#### Scenario: The reference persona has no background key
- **WHEN** the example's `persona` object is inspected
- **THEN** it has exactly the seven card fields and no `background` key

### Requirement: The reference example demonstrates the base-value stats convention correctly
`examples/example_character.json` SHALL set at least one static stat (`atk_phys`, `agility`, or
`defense`) to a base value consistent with its race's documented band, never to a value that would
only make sense with a skill multiplier already applied, matching the schema's own documented
convention (see the `import-schema` capability).

#### Scenario: The example's static stats fall inside its race's documented band
- **WHEN** `examples/example_character.json`'s `race` is `elf` and its `stats.atk_phys` is
  inspected
- **THEN** the value falls within `RACE_REGISTRY["elf"].static_baseline.atk_phys` (70-95 or the
  open-ended prodigy range), not in the tens-of-thousands range a x1000 multiplier would produce

### Requirement: The reference example exercises every major schema branch and a complete NPC card
`examples/example_character.json` SHALL set a `subrace` (exercising the race/subrace cross-check),
a fully populated `stats` object (all eight keys), an empty `disguised_stats` object, non-empty
`skills` and `passives` arrays, a
`sexual_baseline` with `arousal`, `virgin`, `sensitivity`, and at least one additional optional level
field set, and a `persona` that is a complete compact NPC card.

#### Scenario: The example sets a subrace consistent with its race
- **WHEN** `examples/example_character.json`'s `race` and `subrace` fields are inspected
- **THEN** `subrace` resolves in `SUBRACE_REGISTRY` and its `race_key` equals the record's `race`

#### Scenario: The example's stats object sets all eight documented keys
- **WHEN** `examples/example_character.json`'s `stats` object is inspected
- **THEN** it contains exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_power`,
  and `guild_merit`

#### Scenario: The example's disguised_stats stays empty because its race cannot carry a layer
- **WHEN** `examples/example_character.json`'s `disguised_stats` object is inspected
- **THEN** it is empty, because the record's race cannot use divine arts and a non-empty layer on
  such a race is rejected at validation

#### Scenario: The example's sexual_baseline sets an optional field beyond the required three
- **WHEN** `examples/example_character.json`'s `sexual_baseline` object is inspected
- **THEN** it sets `arousal`, `virgin`, and `sensitivity` (the required fields) plus at least one of
  `wetness`, `shame`, `exposure`, or `climax_phase`

#### Scenario: The example's persona is a complete compact card
- **WHEN** `examples/example_character.json`'s `persona` object is inspected through the card contract
- **THEN** it is a valid seven-field compact NPC card

#### Scenario: The example's skills and passives arrays are non-empty
- **WHEN** `examples/example_character.json`'s `skills` and `passives` arrays are inspected
- **THEN** both are non-empty

#### Scenario: A non-empty disguised layer would be rejected by the race guard
- **WHEN** the `disguised_stats` emptiness convention is traced to its enforcement
- **THEN** the record's `human` race cannot use divine arts, so a non-empty layer would be rejected by the `disguised-stats-boundary` capability's race guard
