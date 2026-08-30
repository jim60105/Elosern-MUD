## REMOVED Requirements

### Requirement: can_cast_spell_tier gates casting by element-effective numeric level, overridden by direct mastery ownership
**Reason**: the numeric level gate is a construct of the deleted magic-XP ladder (design D3/D5); no numeric caster stat exists to gate against.
**Migration**: interim cast eligibility is ownership plus MP affordability in `ActionResolver`; `use-driven-skill-lineage` lands the replacement `can_use_skill` gate.

### Requirement: can_cast_skill is the shared side-effect-free cast-eligibility predicate
**Reason**: it composed the deleted element-effective level gate.
**Migration**: `use-driven-skill-lineage`'s `can_use_skill(entity, skill)` replaces it as the single shared predicate; interim callers use ownership + MP checks.
