## MODIFIED Requirements

### Requirement: The six line modules ship pre-declared and pre-imported
`world/skills/sexual_acts/` SHALL contain `solo.py`, `shame.py`, `partner.py`, `combat.py`,
`interspecies.py`, and `divine.py`, each exporting one module-level tuple constant
(`SOLO_ACTS`, `SHAME_ACTS`, `PARTNER_ACTS`, `COMBAT_ACTS`, `INTERSPECIES_ACTS`, `DIVINE_ACTS`
respectively). `solo.py`, `shame.py`, `partner.py`, and `combat.py` carry the seed acts registered
by the `sexual-act-seeds` change. `interspecies.py` (filled by `sexual-catalog-interspecies`) and
`divine.py` (filled by `sexual-catalog-divine-core`) are no longer required to remain empty — every
one of the six modules SHALL export a non-empty tuple once its owning catalog proposal has landed.
`world/skills/sexual_acts/__init__.py` SHALL import all six and merge their contents into
`SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY`.

#### Scenario: The six content modules are importable and non-empty
- **WHEN** each of `solo.py`, `shame.py`, `partner.py`, `combat.py`, `interspecies.py`, and `divine.py`
  is imported after every catalog proposal that fills it has landed
- **THEN** its declared tuple constant exists and is a non-empty tuple of act rows

#### Scenario: A later proposal fills exactly one module with no other line module touched
- **WHEN** a hypothetical catalog proposal changes `solo.py`'s `SOLO_ACTS` tuple to a different
  non-empty tuple of rows and changes no other line module
- **THEN** `SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY` both reflect the new acts after re-import, with
  no edit required to `__init__.py`, `_builder.py`, or any other line module
