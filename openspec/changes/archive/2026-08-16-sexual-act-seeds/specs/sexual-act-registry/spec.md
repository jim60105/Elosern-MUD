## RENAMED Requirements

- FROM: `### Requirement: The six line modules ship pre-declared and pre-imported, each exporting an empty tuple`
- TO: `### Requirement: The six line modules ship pre-declared and pre-imported; 異種 and 神之秘法 remain empty`

## MODIFIED Requirements

### Requirement: The six line modules ship pre-declared and pre-imported; 異種 and 神之秘法 remain empty
`world/skills/sexual_acts/` SHALL contain `solo.py`, `shame.py`, `partner.py`, `combat.py`,
`interspecies.py`, and `divine.py`, each exporting one module-level tuple constant (`SOLO_ACTS`,
`SHAME_ACTS`, `PARTNER_ACTS`, `COMBAT_ACTS`, `INTERSPECIES_ACTS`, `DIVINE_ACTS` respectively).
`solo.py`, `shame.py`, `partner.py`, and `combat.py` carry the seed acts registered by this change;
`interspecies.py` and `divine.py` SHALL remain equal to `()` after this change.
`world/skills/sexual_acts/__init__.py` SHALL import all six and merge their contents into
`SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY`.

#### Scenario: The four content modules are importable and non-empty
- **WHEN** each of `solo.py`, `shame.py`, `partner.py`, and `combat.py` is imported
- **THEN** its declared tuple constant exists and is a non-empty tuple of act rows

#### Scenario: 異種 and 神之秘法 gain no seed
- **WHEN** `interspecies.py`'s `INTERSPECIES_ACTS` and `divine.py`'s `DIVINE_ACTS` are inspected after
  this change
- **THEN** both remain equal to `()`

#### Scenario: A later proposal fills exactly one module with no other file touched
- **WHEN** a hypothetical catalog proposal changes `solo.py`'s `SOLO_ACTS` tuple to a different
  non-empty tuple of rows and changes no other file
- **THEN** `SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY` both reflect the new acts after re-import, with
  no edit required to `__init__.py`, `_builder.py`, or any other line module
