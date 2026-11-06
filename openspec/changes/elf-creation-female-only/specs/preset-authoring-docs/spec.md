## ADDED Requirements

### Requirement: The preset guide documents the race-bounded sex rule
`docs/development/adding-player-presets.md` SHALL document the race-bounded sex rule in its
load-time validator table and its common-mistakes table: the `_validate_preset_sex` row SHALL state
that a declared sex must be permitted by the card's race, the mistake table SHALL carry the elf
declaring a non-female sex with its load-time consequence, and the section's framing sentence SHALL
stay truthful about the validator count.

#### Scenario: The validator row states the race bound
- **WHEN** the guide's load-time validator table is read
- **THEN** the `_validate_preset_sex` row names both the vocabulary membership check and the
  race-permitted check, and carries the message fragment an author actually sees

#### Scenario: The mistake table carries the elf case
- **WHEN** the guide's common-mistakes table is read
- **THEN** an entry states that an elf card declaring a sex other than the permitted one fails at
  lore import, distinct from the already-documented "omitting `sex` raises `TypeError`" entry

#### Scenario: The framing stays accurate
- **WHEN** the section's framing sentence is read
- **THEN** its trigger-point and validator counts match the shipped validator chain, so adding this
  check does not leave an inflated or stale count behind

#### Scenario: The field-set contract is unaffected
- **WHEN** the repo-wide preset guide contract test runs
- **THEN** every `PlayerPreset` field name still appears in the guide as an inline-code span, because
  this requirement adds prose about a rule and no new dataclass field
