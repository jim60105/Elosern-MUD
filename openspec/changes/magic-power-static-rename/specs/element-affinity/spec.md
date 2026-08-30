## MODIFIED Requirements

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
gate-only value: it is never a stored trait, never replaces `magic_power`, and never changes
`magic_power.max` — it exists only for the `can_cast_spell_tier` comparison.

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
