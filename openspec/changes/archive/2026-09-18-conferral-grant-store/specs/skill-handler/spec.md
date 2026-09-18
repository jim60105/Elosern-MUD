## REMOVED Requirements

### Requirement: A skill can confer a scaled-down partial effect of another entity's skill (統御術)
**Reason**: The requirement's shape changes on three axes at once — the store becomes replace-by-key
instead of additive, the scale becomes node data instead of caller-supplied context, and the
deliberately-deferred "casting 統御術 during play is not implemented" clause is exactly what this change
implements. Its scenario set cannot survive a MODIFIED edit, so it is retired and replaced in the same
change (the shipped REMOVED→ADDED precedent used by the element-catalog wave).
**Migration**: None. The project has no released users and stores no conferral data outside
`entity.db.skill_grants`, which the replacement requirement governs from its first write.

## ADDED Requirements

### Requirement: Conferral records a data-scaled grant of every skill its caster owns (統御術)
`world/skills/handler.py` SHALL define a frozen `ConferredSkillGrant` dataclass (`source_key`,
`skill_key`, `scale`) and a read-only `SkillHandler.conferred_grants()` query over the
attribute `entity.db.skill_grants`, kept separate from `entity.db.skills`'s import-populated
`{"active": [...], "passive": [...]}` structure. `trait_keys` is no longer a stored field — it is
derived at resolution time from the referenced skill's own `parsed_effects` rather than duplicated in
the grant record. `effective_value()` SHALL fold every applicable source skill's matching multiplier
multiplied by the grant's fractional `scale` into its multiplier computation, in addition to the
entity's own owned skills. The `skill_owned` rule-table context builder (`world/rules/
combat_modifiers.py`, added by `skill-owned-rule-condition`) SHALL likewise fold a conferred grant's
scaled adjustment into its evaluated bundle when the grant references a skill whose parsed effect is a
`RuleTableEffect`. Conferral of a skill carrying a gate-type effect
(`SexualMasteryEffect`, `DisguiseEffect`) SHALL raise
`EFFECT_RESOLUTION_FAILED` at cast-resolution time rather than silently
applying a no-op scale, and conferral of a skill carrying no continuous-valued
effect any grant consumer can resolve (no `StatMultiplyEffect` and no
`RuleTableEffect`) SHALL likewise be rejected instead of recording a silent
no-op grant. `ElementMasteryEffect` left the gate-type enumeration together
with the retired cast gate (`magic-xp-engine-retirement`): the `<element>_mastery`
skills now carry only the inert `passive_trait:element_mastery` flavor effect and
are therefore rejected by the no-continuous-effect clause instead. The write
primitive SHALL live at
`world.rules.skill_effects.record_conferred_grant()` so `world/skills/` remains
outside the single-writer core.

The store SHALL be keyed by `(source_key, skill_key)`: recording a grant for a pair that already has
one SHALL REPLACE that grant rather than append a second, so a repeated conferral refreshes the scale
instead of compounding the multiplier. Grants from two different sources for the same skill SHALL both
be retained.

The conferral write path SHALL additionally reject a skill that the conferring entity does not
DIRECTLY own at record time, with the same `EFFECT_RESOLUTION_FAILED` rejection the shape validation
uses, so a conferred grant can never exceed — or be chained onward from — what its source itself
holds.

The conferral scale SHALL be read from the conferring skill's own per-occurrence
`EffectPolicy.coefficient` and SHALL NOT be supplied through `event_context`. The conferred SET SHALL
be DERIVED rather than chosen: one grant SHALL be recorded for every skill the caster directly owns
that passes the conferrability shape validation, each at that node's scale. A conferral whose derived
set is empty SHALL raise `EFFECT_RESOLUTION_FAILED` rather than committing an action that records
nothing. The same data-derived scale rule SHALL apply to the conferred growth-rate effect.


#### Scenario: A conferred grant applies its own scale, independent of the source skill's own multiplier
- **WHEN** an entity has no `body_enhancement` skill of its own but has a `ConferredSkillGrant` with
  `skill_key="body_enhancement"`, `scale=0.1` (a ×10 partial effect of a ×100 source skill), and a base
  `atk_phys` of `60`
- **THEN** `entity.skills.effective_value("atk_phys")` returns `600` — a ×10 multiplier — not `6000`
  (which would be the source's own full ×100), with the affected trait(s) derived from
  `body_enhancement`'s own `parsed_effects` rather than a stored `trait_keys` field

#### Scenario: A conferred grant reaches rule-table adjustments, not only stat_multiply
- **WHEN** an entity has a `ConferredSkillGrant` with `skill_key="defense_instinct"`, `scale=0.5`, and
  does not own `defense_instinct` itself
- **THEN** `evaluate_combat_modifiers(entity)`'s bundle includes half of `defense_instinct`'s own
  `skill_owned` rule adjustment

#### Scenario: The deterministic-core primitive records a grant after resolver validation
- **WHEN** `record_conferred_grant(entity, "elosia", "body_enhancement", 0.1)` is called by
  deterministic resolution
- **THEN** `entity.skills.conferred_grants()` includes a `ConferredSkillGrant` with exactly those field
  values

#### Scenario: Conferring a gate-type effect is rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill whose sole
  parsed effect is `SexualMasteryEffect` or `DisguiseEffect`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: Conferring an element-mastery skill is still rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill such as
  `fire_mastery` whose only parsed effect is the retired-cast-gate flavor
  `passive_trait:element_mastery`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` (no continuous-valued effect to scale) and no
  `ConferredSkillGrant` is recorded

#### Scenario: Conferring a skill without any continuous effect is rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill whose
  parsed effects include no `StatMultiplyEffect` and no `RuleTableEffect` (for example a damage-only
  or flavor-only skill)
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: A conferral cast resolves without any supplied event context
- **WHEN** an entity that directly owns at least one conferrable passive casts a conferral skill at a
  valid target through an ordinary cast path, with no conferral keys in `event_context`
- **THEN** the cast resolves and the target holds one grant per conferrable owned skill, each at the
  occurrence's declared scale

#### Scenario: The node's declared scale is the recorded scale
- **WHEN** the conferring occurrence declares a coefficient of `0.25`
- **THEN** every grant the cast records carries `scale == 0.25`, whatever any caller-supplied context
  contains

#### Scenario: A caster with nothing conferrable is rejected, not silently committed
- **WHEN** an entity owning no skill that passes the conferrability shape validation casts a conferral
  skill
- **THEN** the action is rejected with `EFFECT_RESOLUTION_FAILED` and no grant is recorded

#### Scenario: Re-conferring the same skill from the same source replaces the grant
- **WHEN** the same source confers the same skill to the same target twice, at scale `0.1` then `0.25`
- **THEN** `conferred_grants()` holds exactly one grant for that pair, at scale `0.25`, and
  `effective_value()` folds the source multiplier once

#### Scenario: Two different sources conferring the same skill both count
- **WHEN** two different source entities each confer the same skill to one target
- **THEN** `conferred_grants()` holds two grants and both fold into `effective_value()`

#### Scenario: Conferring a skill the source does not own is rejected
- **WHEN** a conferral is attempted for a skill absent from the conferring entity's own owned keys
- **THEN** it raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: A conferred grant cannot be conferred onward
- **WHEN** an entity that holds a skill only as a `ConferredSkillGrant` attempts to confer that same
  skill to a third entity
- **THEN** the attempt is rejected, because the ownership precondition reads direct ownership only
