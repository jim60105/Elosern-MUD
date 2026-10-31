# Spec Delta

## MODIFIED Requirements

### Requirement: The resolver gates scaled casts at the ownership step
`ActionResolver.preflight` and `resolve` SHALL reject a cast with `RejectReason.SCALED_CAST_FORBIDDEN`
when `ActionRequest.scale != 1.0` and any of the following holds: the scale is not a member of the
`freeform_cast_scales` table; `is_freeform_eligible(skill)` is `False`; or the requested scale is not
a member of the skill-anchored `freeform_scales_for(actor, skill)` ladder set.

#### Scenario: A mastery holder can scale an eligible spell
- **GIVEN** fixed synthetic spell, mastery and ladder definitions for the examples below
- **WHEN** `preflight` is called for `t_spell_a` with `scale == 2.0` by an entity who lawfully directly owns the full prerequisite closure of `t_mastery_a` and whose `t_spell_a` proficiency level is >= 6
- **THEN** the freeform check does not reject (other unrelated checks still apply)

#### Scenario: A rung above the current ladder tier is rejected
- **WHEN** `preflight` is called for `t_spell_a` with `scale == 2.0` by a lawful `t_mastery_a` holder
  whose `t_spell_a` proficiency level is 3 (rung tops at 1.0)
- **THEN** it returns `outcome == "rejected"` with `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: Scaling without mastery is rejected
- **WHEN** `preflight` is called for `t_spell_a` with `scale == 2.0` by an entity without
  `t_mastery_a` (even when its innate magic is high)
- **THEN** it returns `outcome == "rejected"` with `RejectReason.SCALED_CAST_FORBIDDEN` and no state
  changes

#### Scenario: Mastery entitles scaling of that element only
- **WHEN** `preflight` is called for `t_spell_b` (an eligible `damage:t_element_b:magic` spell) with
  `scale == 2.0` by an entity lawfully owning only `t_mastery_a`
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN`, because mastery entitlement is element-scoped,
  while the same entity casting `t_spell_a` at `scale == 2.0` passes the freeform gate

#### Scenario: Scaling an ineligible spell is rejected even with mastery
- **WHEN** `preflight` is called for `t_buff` with `scale == 2.0` by an entity lawfully owning
  `t_mastery_a`
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: A non-elemental skill with an MP cost never crashes the gate
- **WHEN** `preflight` is called for `t_elementless` (`mp == 5`, `element is None`) with
  `scale == 2.0` by any entity
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN` without dereferencing a missing element,
  and no exception escapes

#### Scenario: An SP-only elemental skill is not scalable
- **WHEN** `preflight` is called for `t_sp_martial` (element `t_element_c`, `sp` cost only, no `mp`)
  with `scale == 2.0` by a `t_mastery_c` holder
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN` and SP is never deducted

#### Scenario: A non-member scale is rejected
- **WHEN** `preflight` is called for an eligible spell with `scale == 3.0` (not in the table) by a
  lawful mastery holder
- **THEN** it returns `RejectReason.SCALED_CAST_FORBIDDEN`

#### Scenario: Scale one is always permitted
- **WHEN** `preflight` is called with `scale == 1.0` for any owned skill, including non-elemental,
  buff, and mixed-effect spells, by any entity
- **THEN** the freeform check never rejects (other unrelated checks still apply)

#### Scenario: The gate short-circuits in fixed order
- **WHEN** the three gate checks run
- **THEN** they short-circuit in exactly the listed order, so `skill.element` is never dereferenced for an ineligible skill and a non-elemental or cost-less skill can never raise `AttributeError`

#### Scenario: Scale 1.0 bypasses the gate entirely
- **WHEN** a request carries `scale == 1.0`
- **THEN** it bypasses the check entirely and can never be rejected by it

#### Scenario: The gate sits in step-1 ownership validation
- **WHEN** the check runs
- **THEN** it runs inside the existing step-1 ownership validation, before resources or targets, and is side-effect free in preflight

#### Scenario: The ladder set is defined by the mastery specs
- **WHEN** the gate consults the skill-anchored `freeform_scales_for(actor, skill)` ladder set
- **THEN** the ladder is as specified in `element-mastery`, with lawful mastery entitlement and the cast skill's own proficiency per `skill-lineage`

#### Scenario: A bare or invalid mastery rejects scaling
- **WHEN** preflight or resolution requests a non-default scale with a directly owned mastery whose transitive prerequisite closure is unlawful
- **THEN** the freeform gate rejects with SCALED_CAST_FORBIDDEN before resource deduction, while default-scale requests retain the existing bypass
