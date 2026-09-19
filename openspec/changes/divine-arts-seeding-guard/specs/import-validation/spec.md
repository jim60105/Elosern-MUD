## ADDED Requirements

### Requirement: A disguise layer is rejected for a record whose race cannot use divine arts
`validate.py` SHALL reject a character record that declares a non-empty `disguised_stats` while its
race declares that it cannot use divine arts, or while its race does not resolve in the race
registry. The issue SHALL name the record and the `disguised_stats` field, following the batch
report's existing issue shape, and SHALL be a rejection rather than a warning: only the
bloodline-gated veil verb can place a disguise layer, so such a record describes state the engine
would refuse to produce.

This check is independent of the existing subset rule. A record may violate both — declaring a
disguised key absent from `stats` AND declaring a layer its bloodline could not wear — and SHALL then
report both issues rather than stopping at the first.

#### Scenario: A non-divine record carrying a disguise layer is rejected
- **WHEN** a character record declares a race that cannot use divine arts together with a non-empty
  `disguised_stats`
- **THEN** validation reports a rejection naming the record and the `disguised_stats` field, and the
  batch does not load

#### Scenario: A divine-capable record carrying a disguise layer is accepted
- **WHEN** a character record declares a race that can use divine arts together with a
  `disguised_stats` whose keys are a subset of its `stats` keys
- **THEN** validation reports no issue for the layer

#### Scenario: An unresolvable race carrying a disguise layer is rejected
- **WHEN** a character record declares a non-empty `disguised_stats` and a race absent from the race
  registry
- **THEN** validation reports the disguise rejection, because an unresolved race cannot be shown to
  permit a veil

#### Scenario: Both disguise rejections are reported together
- **WHEN** a record on a non-divine race declares a `disguised_stats` key that is also absent from
  its `stats`
- **THEN** the report contains both the subset issue and the bloodline issue

### Requirement: Skill ownership requiring divine arts is rejected for a non-divine record
`validate.py` SHALL reject a character record whose `skills` or `passives` name a registry entry that
requires divine arts while the record's race declares that it cannot use divine arts, or while its
race does not resolve. The issue SHALL name the offending field and key, matching the shape of the
existing unknown-key issue for the same fields.

This mirrors the load-time stance the preset registry already takes for authored preset cards, so the
two authored-content paths agree on what a bloodline permits. When the skill registry is unavailable
and the existing degraded-state reporting applies, this check SHALL degrade with it rather than
rejecting every record.

#### Scenario: A non-divine record owning a divine-arts skill is rejected
- **WHEN** a character record declares a race that cannot use divine arts and lists a divine-arts
  skill in `skills`
- **THEN** validation reports a rejection naming the field and the key, and the batch does not load

#### Scenario: The same rule applies to passives
- **WHEN** such a record lists a divine-arts skill in `passives` instead
- **THEN** validation reports the equivalent rejection

#### Scenario: A divine-capable record owning a divine-arts skill is accepted
- **WHEN** a character record declares a race that can use divine arts and lists a divine-arts skill
- **THEN** validation reports no issue for that entry

#### Scenario: A non-divine skill is unaffected
- **WHEN** a record on a non-divine race lists a registry skill that does not require divine arts
- **THEN** validation reports no issue for that entry

#### Scenario: The check degrades with the skill registry
- **WHEN** the skill registry is unavailable and the existing degraded-state reporting is in effect
- **THEN** the bloodline check reports nothing rather than rejecting, exactly as the unknown-key check
  does in the same state
