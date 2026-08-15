## ADDED Requirements

### Requirement: The no-create preview path resolves the derived arousal level from stored pleasure, not a raw arousal key
`world/rules/combat_modifiers.py::build_no_create_condition_context()` SHALL resolve its `"arousal"`
context entry from the persisted `pleasure` counter's stored value (via the same band lookup
`SexualState.arousal` uses at read time), for any entity whose `sexual_traits` handler has been
materialized, rather than from a raw `"arousal"` key — which SHALL NOT exist in that storage once an
entity's `SexualState` has been built. For an entity whose handler has never been materialized, this
path SHALL still read `"arousal"` as a level string from the entity's frozen import-time baseline
Attribute, unchanged from before this capability's amendment. This resolution SHALL NOT read
`entity.sexual`, construct a `TraitHandler`, or otherwise materialize any persistent state.

#### Scenario: The preview path reflects live pleasure on a materialized entity
- **WHEN** an entity's `SexualState` has been materialized and its `pleasure` has since been raised at
  runtime (through any path) past the `高度` band's floor, and
  `evaluate_combat_modifiers_no_create(entity)` is called without first reading `entity.sexual`
  directly
- **THEN** the returned bundle includes `high_arousal_agility_accuracy_penalty`'s adjustment,
  matching what `evaluate_combat_modifiers(entity)` (the live, handler-based path) reports for the
  same entity at the same moment

#### Scenario: An unmaterialized entity still resolves from its import baseline
- **WHEN** an entity has a populated import-time sexual baseline but no materialized `sexual_traits`
  handler, and `evaluate_combat_modifiers_no_create(entity)` is called
- **THEN** the resolved `"arousal"` context value matches the baseline's `arousal` level string, and
  no `sexual_traits` Attribute is created as a result of the call

#### Scenario: The no-create path never diverges from the live path for the same entity
- **WHEN** `evaluate_combat_modifiers(entity)` (materializing) and
  `evaluate_combat_modifiers_no_create(entity)` (non-materializing) are both called on the same
  already-materialized entity, in either order, with no state change between the two calls
- **THEN** both return the same arousal-driven adjustment bundle
