## ADDED Requirements

### Requirement: The reference example exercises every major schema branch it can demonstrate on its race
`examples/example_character.json` SHALL set a `subrace` (exercising the race/subrace cross-check),
a fully populated `stats` object (all eight keys), an empty `disguised_stats` object (the record's
`human` race cannot use divine arts, so a non-empty layer would be rejected by the
`disguised-stats-boundary` capability's race guard), non-empty `skills` and `passives` arrays, a
`sexual_baseline` with `arousal`, `virgin`, `sensitivity`, and at least one additional optional level
field set, and a non-empty, multi-key `persona` object.

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

#### Scenario: The example's persona is a non-trivial, multi-key opaque object
- **WHEN** `examples/example_character.json`'s `persona` object is inspected
- **THEN** it contains more than one top-level key, and no test anywhere inspects its nested content
  beyond confirming it is an object

## REMOVED Requirements

### Requirement: The reference example exercises every major schema branch
**Reason**: This change (divine-arts-seeding-guard) rejects a non-empty `disguised_stats` on any
record whose race cannot use divine arts. The reference example is `race: "human"`, which cannot use
divine arts, so it can no longer demonstrate a populated, non-empty disguise layer without violating
the new boundary rule. Replaced by "...it can demonstrate on its race", whose disguised_stats
scenario demonstrates the field staying empty instead.
**Migration**: None — pre-release, no consumers depend on the removed scenario's assertion that the
layer is non-empty.

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
- **THEN** it contains exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_power`,
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
