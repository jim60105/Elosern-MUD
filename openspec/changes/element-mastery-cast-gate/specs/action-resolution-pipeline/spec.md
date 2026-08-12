## ADDED Requirements

### Requirement: Casting an elemental spell above the caster's tier without mastery is rejected
`ActionResolver.preflight` and `resolve` SHALL additionally reject a cast whose target skill is an
elemental spell when `can_cast_spell_tier(caster, element, tier)` returns `False`, using the same
rejection category already used for unowned-skill casts (no new `RejectReason` member).

#### Scenario: Preflight rejects an under-tier cast with no mastery
- **WHEN** `preflight` is called for a cast of a 賢者-tier fire spell by an entity with
  `magic_level.value == 20` and no owned `fire_mastery`
- **THEN** it returns the same rejection category as an unowned-skill cast

#### Scenario: An entity meeting the tier or holding mastery passes this check
- **WHEN** `preflight` is called for a cast of a 賢者-tier fire spell by an entity with either
  `magic_level.value >= 71` or owned `fire_mastery`
- **THEN** this check does not reject the cast (other unrelated checks still apply normally)
