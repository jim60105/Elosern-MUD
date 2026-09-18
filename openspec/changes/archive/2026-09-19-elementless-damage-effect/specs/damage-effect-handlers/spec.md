## MODIFIED Requirements

### Requirement: damage:<element>:<school> is the defined convention for this prefix
`_handle_damage` SHALL parse `effect_id` as `damage:<element>:<school>`, matching the change-5 seed
registry, where `school` is either `"physical"` (reading `atk_phys`) or `"magic"` (reading
`magic_power`) as the attacking stat, and `element` either references
`world.lore.elements.ELEMENT_REGISTRY` or is the reserved token `none`, which denotes the absence of
an element rather than a registry lookup. The reserved token SHALL change nothing about settlement:
the school segment alone selects the attacking stat, and an elementless damage effect resolves
through the same to-hit roll, defense subtraction, policy application and projection as an
element-bearing one.

#### Scenario: A physical damage effect reads atk_phys
- **WHEN** `_handle_damage` processes an effect ID of `"damage:dark:physical"`
- **THEN** the attacking stat is `SkillHandler.effective_value("atk_phys")` for the acting entity

#### Scenario: A magic damage effect reads magic_power
- **WHEN** `_handle_damage` processes an effect ID of `"damage:fire:magic"`
- **THEN** the attacking stat is `SkillHandler.effective_value("magic_power")` for the acting entity

#### Scenario: An elementless physical effect settles identically to an element-bearing one
- **WHEN** a synthetic actor strikes a target with an elementless physical damage effect, and a twin
  actor strikes an identical target with an element-bearing physical damage effect of the same
  coefficient and policy under the same fixed roll
- **THEN** both attacks read `atk_phys`, subtract the same defense, apply the same policy terms and
  commit the same hp delta, and neither the attacker's nor the target's elemental affinity changes
  either result
