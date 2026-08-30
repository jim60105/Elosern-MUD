## Purpose

Element affinity derives a finite per-element multiplier from an entity's
stored affinity set, giving favored elements faster magic-tier progression and
non-favored elements slower progression. The affinity set is a single validated
per-entity source of truth written only through the deterministic identity
channels (preset, custom creation, import); the multiplier is a transient
gate-only value and never a stored trait.

## Requirements

### Requirement: element_affinity_multiplier derives a finite per-element multiplier
`world/rules/progression.py` SHALL define `element_affinity_multiplier(entity, element: str) ->
float` as a pure read-only query that reads `entity.db.affinity_elements` and returns exactly `1.1`
when `element` is in that collection, `0.9` when the collection is non-empty and `element` is not in
it, and `1.0` when the collection is empty or absent. The `1.1` and `0.9` constants SHALL be read
from `progression.yaml` (`affinity_element_multiplier` / `non_affinity_element_multiplier`) and SHALL
be finite and non-negative. An unrecognized element key SHALL raise `ValueError`. This function SHALL
NOT write any entity attribute.

#### Scenario: A neutral entity returns 1.0 for every element
- **WHEN** `element_affinity_multiplier(entity, "fire")` is called on an entity with no
  `entity.db.affinity_elements`
- **THEN** it returns exactly `1.0`

#### Scenario: A favored element returns the affinity multiplier
- **WHEN** `element_affinity_multiplier(entity, "fire")` is called on an entity with
  `entity.db.affinity_elements == ["fire", "wind"]`
- **THEN** it returns exactly the yaml `affinity_element_multiplier` value (`1.1`)

#### Scenario: A non-favored element on an affinity-bearing entity returns the non-affinity multiplier
- **WHEN** `element_affinity_multiplier(entity, "water")` is called on an entity with
  `entity.db.affinity_elements == ["fire"]`
- **THEN** it returns exactly the yaml `non_affinity_element_multiplier` value (`0.9`)

#### Scenario: An unknown element key fails closed
- **WHEN** `element_affinity_multiplier(entity, "not_an_element")` is called
- **THEN** it raises `ValueError` and no attribute is written

### Requirement: affinity_elements is one validated per-entity source of truth
An entity's affinity set SHALL be stored in exactly one attribute, `entity.db.affinity_elements`, as
a list of lowercase, de-duplicated element keys each present in `ELEMENT_REGISTRY`. Every identity
channel that grants affinities (player preset, custom creation, character import) SHALL write this
attribute inside its normal all-or-nothing write; no rule SHALL consult `Subrace.affinity_elements`
at cast time. For elves the subrace is the sole affinity authority in every channel: the set is
always seeded from `SUBRACE_REGISTRY[subrace].affinity_elements`, an elf preset SHALL declare an
empty set (validated at registry load), and an elf-supplied set from custom creation or import SHALL
be rejected. The subrace seed itself SHALL be validated (every key exists in `ELEMENT_REGISTRY`, no
duplicates) when the registry loads or when the seed is resolved, so an invalid seed can never be
persisted. An entity with an empty or absent affinity set is neutral and gets the `1.0` multiplier
for every element. The element-effective magic level derived from the multiplier is a transient
gate-only value: it is never a stored trait, never replaces the `magic_power` trait value, and
never changes the owning race's `static_baseline.magic_power` band — it exists only for the
`can_cast_spell_tier` comparison.

#### Scenario: An elf subrace seed may exceed the player input bound
- **WHEN** an eolas elf activates with `SUBRACE_REGISTRY["eolas"].affinity_elements` (all eight
  elements) as its seed
- **THEN** `entity.db.affinity_elements` contains all eight element keys and every element is
  favored (×1.1)

#### Scenario: A neutral preset (no affinity) stays neutral
- **WHEN** a preset with an empty `affinity_elements` activates
- **THEN** `entity.db.affinity_elements` is empty and every element keeps the `1.0` multiplier

#### Scenario: An elf identity channel cannot contradict its subrace
- **WHEN** an elf preset declares a non-empty affinity set, or an elf custom/import record supplies
  one
- **THEN** the preset fails at registry load, and the custom/import record is rejected, leaving the
  subrace seed as the elf's only affinity source

#### Scenario: An invalid subrace seed fails closed
- **WHEN** a subrace's `affinity_elements` contains an unknown element key or a duplicate
- **THEN** registry load or seed resolution raises, and no entity persists the invalid set
