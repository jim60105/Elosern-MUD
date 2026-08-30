## MODIFIED Requirements

### Requirement: damage:<element>:<school> is the defined convention for this prefix
`_handle_damage` SHALL parse `effect_id` as `damage:<element>:<school>`, matching the change-5 seed
registry, where `school` is either `"physical"` (reading `atk_phys`) or `"magic"` (reading
`magic_power`) as the attacking stat, and `element` references
`world.lore.elements.ELEMENT_REGISTRY`.

#### Scenario: A physical damage effect reads atk_phys
- **WHEN** `_handle_damage` processes an effect ID of `"damage:dark:physical"`
- **THEN** the attacking stat is `SkillHandler.effective_value("atk_phys")` for the acting entity

#### Scenario: A magic damage effect reads magic_power
- **WHEN** `_handle_damage` processes an effect ID of `"damage:fire:magic"`
- **THEN** the attacking stat is `SkillHandler.effective_value("magic_power")` for the acting entity

### Requirement: Damage reads every stat through effective_value(), never raw entity.traits
`_handle_damage` SHALL read `atk_phys`/`magic_power`, `agility`, and `defense` exclusively through
`SkillHandler.effective_value()` for both the acting entity and every target — never
`entity.traits.<key>.value` directly — so that an active stat-multiplier skill's ×10/×100/×1000
applies at resolution time.

#### Scenario: An active body-enhancement skill changes computed damage without changing stored stats
- **WHEN** an attacker with an active ×100 body-enhancement skill casts a `damage:physical` skill
- **THEN** the resulting damage reflects the multiplied `atk_phys`, while
  `entity.traits.atk_phys.value` is unchanged before and after the action
