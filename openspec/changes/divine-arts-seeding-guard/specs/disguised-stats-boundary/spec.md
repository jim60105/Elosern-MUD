## ADDED Requirements

### Requirement: Only an entity that can use divine arts may be seeded with a disguise layer
A disguise layer SHALL exist only on an entity whose race declares that it can use divine arts. The
veil verb is bloodline-gated, and nothing else in the game writes a disguise layer, so a veil on any
other entity describes state the engine would refuse to produce.

Every SEEDING boundary SHALL enforce this before the layer can be persisted: the lore-registry
validation that admits authored preset cards, and the import validation that admits authored records.
Enforcement SHALL fail closed — a race that does not resolve is treated as unable to use divine arts,
so an unknown race cannot smuggle a veil past the check.

The check SHALL read the race's declared divine-arts capability rather than inspecting skill
ownership, so an entity is judged on whether its bloodline could ever place a veil, not on whether
this particular declaration happens to list the veil skill.

This requirement bounds the layer's WEARER. It does not change which values the layer may hold, who
may read it, or which modules may write it; those remain governed by this capability's existing
requirements.

#### Scenario: An authored preset on a non-divine race may not declare a disguise layer
- **WHEN** a preset card whose race cannot use divine arts declares a non-empty `disguised_stats`
- **THEN** lore-registry validation raises at import, naming the preset and the violation, and the
  registry does not load

#### Scenario: An authored preset on a divine-capable race may declare one
- **WHEN** a preset card whose race can use divine arts declares a well-formed `disguised_stats`
- **THEN** validation accepts it, exactly as before this change

#### Scenario: An imported record on a non-divine race may not carry a disguise layer
- **WHEN** a character record whose race cannot use divine arts declares a non-empty `disguised_stats`
- **THEN** import validation reports a rejection naming the record and the field, and no entity is
  constructed

#### Scenario: An unresolvable race cannot carry a disguise layer
- **WHEN** a preset card or a character record declares a disguise layer alongside a race that does
  not resolve in the race registry
- **THEN** the disguise layer is rejected, because an unresolved race is treated as unable to use
  divine arts

#### Scenario: An empty declaration is not a disguise layer
- **WHEN** a preset card or a character record on a non-divine race declares an empty
  `disguised_stats`
- **THEN** validation accepts it, because no layer is seeded
