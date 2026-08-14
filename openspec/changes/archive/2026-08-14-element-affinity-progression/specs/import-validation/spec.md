## ADDED Requirements

### Requirement: Import validation enforces race-aware affinity counts and registry membership
`validate.py` SHALL reject a character record whose `affinity_elements` (when present) contains an
element key absent from `world.lore.elements.ELEMENT_REGISTRY` or a duplicate, and SHALL reject a
count that exceeds the race bound: at most 2 for a `human`, at most 1 for a `beastfolk`, and none
for an `elf` (an elf's affinity is subrace-derived, so an elf record SHALL NOT supply
`affinity_elements` at all). A record with no `affinity_elements` SHALL produce no rejection for
this check.

#### Scenario: An unknown affinity element is rejected
- **WHEN** a character record's `affinity_elements` includes `"luck"`
- **THEN** the record is rejected, naming the `affinity_elements` field and the unknown key

#### Scenario: A duplicate affinity element is rejected
- **WHEN** a character record's `affinity_elements` is `["fire", "fire"]`
- **THEN** the record is rejected, naming the duplicate

#### Scenario: A human with three affinity elements is rejected
- **WHEN** a `human` character record's `affinity_elements` contains 3 elements
- **THEN** the record is rejected on the human two-element bound

#### Scenario: A beastfolk with two affinity elements is rejected
- **WHEN** a `beastfolk` character record's `affinity_elements` contains 2 elements
- **THEN** the record is rejected on the beastfolk one-element bound

#### Scenario: An elf record supplying an affinity set is rejected
- **WHEN** an `elf` character record's `affinity_elements` is present at all — non-empty or an empty
  array
- **THEN** the record is rejected, naming the elf subrace-authority rule, and no elf-persisted set
  can contradict the subrace

#### Scenario: A record without affinity_elements is not rejected for that reason
- **WHEN** a character record omits `affinity_elements` entirely
- **THEN** no rejection is produced for the affinity check; a human or beastfolk record loads as
  neutral, and an elf record loads with the subrace seed
