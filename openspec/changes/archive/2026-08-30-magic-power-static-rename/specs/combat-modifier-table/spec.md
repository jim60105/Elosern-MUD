## MODIFIED Requirements

### Requirement: Flat defense and atk_phys bundle values adjust deterministic damage magnitude
Damage resolution in `world/rules/combat.py`'s damage handler SHALL add the actor's flat `atk_phys`
bundle value to the actor's effective physical attack stat before the damage multiplier is applied,
and SHALL add the target's flat `defense` bundle value to the target's effective defense stat before
the defense term is subtracted. The `atk_phys` adjustment SHALL apply only to physical-school
attacks (`attack_key == "atk_phys"`); magic-school attacks (`magic_power`) SHALL NOT receive it. The
`defense` adjustment SHALL apply to both physical and magic attacks, matching defense's existing
dual-school mitigation role. An entity with no matching rows receives unchanged damage math.

#### Scenario: A physical attacker with an atk_phys bonus deals more damage
- **WHEN** an entity owning `retainer_martial_training` (bundle `atk_phys: 5`) lands a physical
  attack whose magnitude would otherwise be `round(effective_atk * multiplier) - defense`
- **THEN** the staged damage amount equals `round((effective_atk + 5) * multiplier) - defense`,
  floored at the configured damage floor

#### Scenario: A magic attack ignores the atk_phys bonus
- **WHEN** the same attacker casts a magic-school spell (damage effect with the magic school)
- **THEN** the staged damage amount is computed from `effective_value("magic_power")` with no
  `atk_phys` bundle value added

#### Scenario: A defender with a defense bonus takes less damage
- **WHEN** an entity owning `guardian_instinct` (bundle `defense: 5`) is the target of a physical
  or magic attack
- **THEN** the staged damage amount equals `round(attack * multiplier) - (effective_defense + 5)`,
  floored at the configured damage floor
