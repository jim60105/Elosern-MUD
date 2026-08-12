## MODIFIED Requirements

### Requirement: A skill can confer a scaled-down partial effect of another entity's skill (統御術)
`world/skills/handler.py` SHALL define a frozen `ConferredSkillGrant` dataclass (`source_key`,
`skill_key`, `scale`) and a read-only `SkillHandler.conferred_grants()` query over the additive
attribute `entity.db.skill_grants`, kept separate from `entity.db.skills`'s import-populated
`{"active": [...], "passive": [...]}` structure. `trait_keys` is no longer a stored field — it is
derived at resolution time from the referenced skill's own `parsed_effects` rather than duplicated in
the grant record. `effective_value()` SHALL fold every applicable source skill's matching multiplier
multiplied by the grant's fractional `scale` into its multiplier computation, in addition to the
entity's own owned skills. The `skill_owned` rule-table context builder (`world/rules/
combat_modifiers.py`, added by `skill-owned-rule-condition`) SHALL likewise fold a conferred grant's
scaled adjustment into its evaluated bundle when the grant references a skill whose parsed effect is a
`RuleTableEffect`. Conferral of a gate-type effect (`ElementMasteryEffect`, `SexualMasteryEffect`,
`DisguiseEffect`) SHALL raise `EFFECT_RESOLUTION_FAILED` at cast-resolution time rather than silently
applying a no-op scale. The write primitive SHALL live at
`world.rules.skill_effects.record_conferred_grant()` so `world/skills/` remains outside the
single-writer core.

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
  parsed effect is `ElementMasteryEffect`, `SexualMasteryEffect`, or `DisguiseEffect`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: Casting 統御術 during play is not implemented by this change
- **WHEN** the codebase added by this change is inspected for any code path that creates a
  `ConferredSkillGrant` as a result of resource checks, targeting, or an `ActionResolver`-style
  invocation
- **THEN** no such code path exists — this change generalizes the persistence primitive and its
  consumers only; the cast-time `_handle_confer_skill_partial` handler in `action.py` (already landed)
  is updated to stop passing `confer_trait_keys` in its event context, since the field no longer exists
