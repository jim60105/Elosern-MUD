## MODIFIED Requirements

### Requirement: LivingEntity non-trait handlers are working implementations including persona
`LivingEntity` SHALL expose `traits`, `sexual`, `buffs`, `equipment`, `skills`, `relations`, and
`persona` as working handlers (each owned by its capability change: traits by entity-traits,
sexual by the sexual-state handler, buffs by the buff-handler integration, equipment and skills by
equipment-inventory and the skill handler, relations by the affinity capability, persona by the
persona-store capability). `persona` SHALL be a `PersonaStore` mount backed by the verbatim
`entity.db.persona` record.

#### Scenario: Non-trait handlers exist as working implementations
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.traits` is a `TraitHandler`, `entity.sexual` is a `SexualState`,
  `entity.buffs` is a `BuffHandler`, `entity.equipment` is an `EquipmentHandler`,
  `entity.skills` is a `SkillHandler`, and `entity.relations` is a `RelationHandler` backed by the
  `relations_data` attribute

#### Scenario: persona is a working PersonaStore mount
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.persona` is a `PersonaStore` instance reading the `entity.db.persona` record,
  and its `flatten()` returns `None` when no persona record exists

#### Scenario: The PersonaStore implementation is authored by its owning change
- **WHEN** the codebase is inspected after the persona-store change lands
- **THEN** `world/rules/persona.py` defines the `PersonaStore` class and no `AttributeProperty`
  persona placeholder remains on `LivingEntity`
