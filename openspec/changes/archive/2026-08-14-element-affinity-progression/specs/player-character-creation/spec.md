## ADDED Requirements

### Requirement: Custom creation collects a race-bounded affinity element set
Custom mode SHALL additionally collect an optional element-affinity set whose size bound depends on
the selected race: a human may pick at most 2 elements, a beastfolk at most 1, and an elf picks none
(an elf's affinity set SHALL be derived from the chosen subrace's `affinity_elements`, and a
player-supplied affinity set on an elf SHALL be rejected). Every supplied element SHALL be a
lowercase key present in `ELEMENT_REGISTRY`, with no duplicates. Preset mode SHALL not collect an
affinity set; it SHALL derive the set from the selected preset's declared `affinity_elements`.
Activation SHALL write the resulting set to `entity.db.affinity_elements` inside the same
all-or-nothing activation transaction that writes identity, traits, and the remaining initial
mechanical state. An empty set yields neutral progression (×1.0 for every element).

#### Scenario: A human custom character picks two affinity elements
- **WHEN** custom creation chooses `race == "human"` and supplies `affinity_elements == ["fire",
  "wind"]`
- **THEN** activation persists `entity.db.affinity_elements == ["fire", "wind"]` and both elements
  are favored

#### Scenario: A human picking a third element is rejected
- **WHEN** custom creation chooses `race == "human"` and supplies three elements
- **THEN** activation is rejected before persistence with an explanation of the two-element human
  bound

#### Scenario: A beastfolk picks at most one affinity element
- **WHEN** custom creation chooses `race == "beastfolk"` and supplies exactly one element
- **THEN** activation persists that single element, while a two-element beastfolk request is
  rejected before persistence

#### Scenario: An elf cannot supply an affinity set
- **WHEN** custom creation chooses `race == "elf"` and supplies any player-chosen affinity set
- **THEN** activation is rejected before persistence, and the elf's affinity set is instead seeded
  from the chosen subrace's `affinity_elements`

#### Scenario: An elf subrace seeds the affinity set at activation
- **WHEN** custom creation chooses `race == "elf"` and `subrace == "fionnen"` with no affinity input
- **THEN** activation persists `entity.db.affinity_elements == ["light"]`, matching
  `SUBRACE_REGISTRY["fionnen"].affinity_elements`

#### Scenario: Unknown or duplicate affinity elements are rejected
- **WHEN** custom creation supplies an element key absent from `ELEMENT_REGISTRY`, or repeats the
  same element twice
- **THEN** activation is rejected before persistence

### Requirement: Preset activation persists the preset's declared affinity set
Preset mode SHALL persist the selected preset's `affinity_elements` (possibly empty) into
`entity.db.affinity_elements` in the same all-or-nothing activation transaction that grants the
preset's skill kit. An elf preset SHALL declare an empty set — the elf's set is seeded from its
subrace at activation, never from the preset. The registry SHALL reject a preset whose declared
affinity elements include an unknown key, a duplicate, or (for an elf preset) any element — at
registry load, never at player activation.

#### Scenario: A preset with declared affinities activates with them
- **WHEN** a pending player activates a human or beastfolk preset whose `affinity_elements ==
  ["fire", "wind"]`
- **THEN** the activated character's `entity.db.affinity_elements` equals `["fire", "wind"]`

#### Scenario: A preset with an empty affinity set stays neutral
- **WHEN** a pending player activates a preset whose `affinity_elements` is empty
- **THEN** the activated character's `entity.db.affinity_elements` is empty and every element keeps
  the neutral ×1.0 multiplier

#### Scenario: An elf preset activates with its subrace seed, not a preset set
- **WHEN** a pending player activates an elf preset whose race/subrace is `fionnen`
- **THEN** the activated character's `entity.db.affinity_elements` equals
  `SUBRACE_REGISTRY["fionnen"].affinity_elements` (`["light"]`) regardless of the preset's own
  (empty) field

#### Scenario: A preset with an invalid affinity element fails at load
- **WHEN** a preset declares an affinity element absent from `ELEMENT_REGISTRY`, a duplicate, or any
  non-empty set on an elf preset
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation
