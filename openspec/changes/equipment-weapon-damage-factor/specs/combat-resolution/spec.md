# Spec Delta

## ADDED Requirements

### Requirement: Physical damage multiplies the rounded attack component by equipped weapon factor
Physical-school attack_part SHALL be round(attack * roll_multiplier * coefficient * matched_multiplier * weapon_multiplier) before ratio mitigation. Element-bearing physical damage SHALL use the same factor. Magic and healing SHALL NOT use it. Existing strike counts, traits, proficiency access and practice affinity SHALL remain unchanged.

#### Scenario: Independent weapon and magic controls
- **WHEN** K=40, defense=20, attack before weapon factor=60 and the declared physical factor is 1.5
- **THEN** physical damage before Defend is 60; the matching magic control remains 40 and healing remains unchanged

#### Scenario: Multiple strikes and estimation
- **WHEN** an existing multi-strike physical skill resolves or is estimated
- **THEN** each existing strike uses the factor once and the strike count is unchanged; settlement and estimate agree

#### Scenario: No character multiplier growth
- **WHEN** proficiency, guild rank or elemental practice affinity changes without equipment change
- **THEN** no weapon factor or stored base trait changes


