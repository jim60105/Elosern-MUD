## ADDED Requirements

### Requirement: dual_wield_style grants a combat adjustment while owned
`combat_modifiers.yaml` SHALL contain a `skill_owned` row for `dual_wield_style` producing a nonzero
to-hit and/or damage adjustment, conditioned on actual dual-wielding if the equipment data model
exposes that fact as a queryable condition, or on bare ownership otherwise.

#### Scenario: Owning and dual-wielding grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that owns `dual_wield_style` and
  (if the equipment check is implemented) has two weapons equipped
- **THEN** the returned bundle includes `dual_wield_style`'s adjustment

#### Scenario: Not owning the skill never grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that does not own
  `dual_wield_style`
- **THEN** the returned bundle does not include this adjustment, regardless of equipped weapons
