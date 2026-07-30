## ADDED Requirements

### Requirement: One valid, adult-compliant reference character card exists and stays valid
`world/imports/examples/example_character.json` SHALL be a single character record with
`"record_type": "character"`, satisfying `CHARACTER_SCHEMA_V1` and every semantic validation rule
with zero rejections, with `age` and `apparent_age` both at least 18. A permanent test SHALL load
this file and assert it produces zero rejections and zero warnings against the current schema and
lore registries.

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

#### Scenario: The reference example is an adult, not a boundary-value probe
- **WHEN** `examples/example_character.json`'s `age` and `apparent_age` are inspected
- **THEN** both are comfortably above 18 (not exactly 18), so the reference card reads as an
  unambiguous adult character rather than an edge-case demonstration

### Requirement: The reference example exercises every major schema branch
`examples/example_character.json` SHALL set a `subrace` (exercising the race/subrace cross-check),
a fully populated `stats` object (all eight keys), a `disguised_stats` object that is a proper,
non-empty subset of `stats`' keys, non-empty `skills` and `passives` arrays, a `sexual_baseline`
with `arousal`, `virgin`, `sensitivity`, and at least one additional optional level field set, and a
non-empty, multi-key `persona` object.

#### Scenario: The example sets a subrace consistent with its race
- **WHEN** `examples/example_character.json`'s `race` and `subrace` fields are inspected
- **THEN** `subrace` resolves in `SUBRACE_REGISTRY` and its `race_key` equals the record's `race`

#### Scenario: The example's stats object sets all eight documented keys
- **WHEN** `examples/example_character.json`'s `stats` object is inspected
- **THEN** it contains exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_level`,
  and `guild_merit`

#### Scenario: The example's disguised_stats is a non-empty, proper subset of stats keys
- **WHEN** `examples/example_character.json`'s `disguised_stats` keys are compared against its
  `stats` keys
- **THEN** every `disguised_stats` key is also a `stats` key, and at least one key is set

#### Scenario: The example's sexual_baseline sets an optional field beyond the required three
- **WHEN** `examples/example_character.json`'s `sexual_baseline` object is inspected
- **THEN** it sets `arousal`, `virgin`, and `sensitivity` (the required fields) plus at least one of
  `wetness`, `shame`, `exposure`, or `climax_phase`

#### Scenario: The example's persona is a non-trivial, multi-key opaque object
- **WHEN** `examples/example_character.json`'s `persona` object is inspected
- **THEN** it contains more than one top-level key, and no test anywhere inspects its nested content
  beyond confirming it is an object

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
