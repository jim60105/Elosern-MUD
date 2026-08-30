## MODIFIED Requirements

### Requirement: The conferred growth-rate buff's tick is a documented no-op, consumed by pull rather
than push
`_apply_rate_modifier()` SHALL treat `skill_practice` (the `conferred_growth_rate` buff's declared
`rate` target) as an explicit, documented no-op on tick, not an unimplemented or erroring case. The
buff's `scale` SHALL be consumed exclusively by pull, through `growth_rate_multiplier(entity)` (the query has no live reader after the magic-XP engine's retirement and will be read
again when `use-driven-skill-lineage` re-anchors the practice-XP formula onto it), and SHALL
NOT be additionally applied as a per-tick effect. This SHALL be stated in `_apply_rate_modifier()`'s own
docstring, naming `growth_rate_multiplier()`/change 11b as the actual reader, so a future edit does not
reintroduce a push-side application and double-count the scale.

#### Scenario: Ticking a conferred growth-rate buff completes without raising
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
  (applied via `grant_conferred_growth_rate`)
- **THEN** it completes without raising `NotImplementedError` or any other exception

#### Scenario: Ticking a conferred growth-rate buff leaves magic_power untouched
- **WHEN** `tick_buffs(entity)` is called on an entity holding an active `conferred_growth_rate` buff
- **THEN** `entity.traits.magic_power.value` and `entity.db.skill_proficiency` are unchanged
  before and after the call, and no other entity attribute is mutated as a result of this buff's
  tick

#### Scenario: The no-op is documented as intentional, not a placeholder gap
- **WHEN** `_apply_rate_modifier()`'s docstring is inspected for the `skill_practice` branch
- **THEN** it states that the value is read by pull through `growth_rate_multiplier()` (change 11b's
  growth multiplier query), and that applying it again on tick would double-apply the
  conferred scale
