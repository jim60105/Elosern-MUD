## RENAMED Requirements

- FROM: `### Requirement: Non-trait LivingEntity handlers are declared seams, not implementations`
- TO: `### Requirement: LivingEntity non-trait handlers are working implementations except persona, which remains a declared seam`

## MODIFIED Requirements

### Requirement: LivingEntity non-trait handlers are working implementations except persona, which remains a declared seam
`LivingEntity` SHALL expose `traits`, `sexual`, `buffs`, `equipment`, `skills`, and `relations`
as working handlers (each owned by its capability change: traits by entity-traits, sexual by the
sexual-state handler, buffs by the buff-handler integration, equipment and skills by
equipment-inventory and the skill handler, relations by the affinity capability). `persona` SHALL
remain a placeholder attribute defaulting to `None` with no behavior implemented.

#### Scenario: Non-trait handlers exist as working implementations
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.traits` is a `TraitHandler`, `entity.sexual` is a `SexualState`,
  `entity.buffs` is a `BuffHandler`, `entity.equipment` is an `EquipmentHandler`,
  `entity.skills` is a `SkillHandler`, and `entity.relations` is a `RelationHandler` backed by the
  `relations_data` attribute

#### Scenario: persona remains a declared seam
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.persona` is present as an attribute and equals `None`

#### Scenario: No PersonaStore implementation is authored
- **WHEN** the codebase added by this change is inspected
- **THEN** it contains no `PersonaStore` class definition — persona stays a forward-declared seam
  owned by a later change
