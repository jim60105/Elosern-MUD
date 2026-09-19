## MODIFIED Requirements

### Requirement: Successful ACTIVE resolution accruses lineage practice XP
Every successful ACTIVE skill resolution SHALL accrue to the actor, inside the existing action
snapshot/restore face and the same transaction as the skill's own effects: `SKILL_PRACTICE_XP_PER_USE
× RACE_REGISTRY[race].learning_multiplier × element_affinity_multiplier(entity, skill.element)`
(physical or non-elemental skills multiply by `1.0`) `× growth_rate_multiplier(entity)` (the
conferred-buff pull path) `× the owned-skill growth factor`. The owned-skill growth factor SHALL be
the product of the multipliers of every scoped `growth_rate` effect carried by a skill the actor
OWNS whose declared scope equals the element of the skill being practised; it SHALL be `1.0` for a
skill of any other element and for a skill declaring no element, so an unscoped acceleration is not
expressible. This factor is independent of the conferred-buff factor: the two multiply, and neither
reads the other. The affinity factor SHALL apply only to a skill whose parsed effects
include a magic-school damage of its own element — a physical skill carrying an element (e.g.
`light_sword_style`) multiplies by `1.0`, and so does a physical skill declaring no element at all. Storage and derivation are unchanged:
`db.skill_proficiency[skill_key]` float XP with `level = floor(xp / 50)`. PASSIVE skills SHALL NOT
accrue. A resolution carrying the simulated marker (a guild examination's
`event_context["simulated"]`) SHALL accrue nothing. Accrual SHALL NOT read the actor's school or any
magic stat.

Exactly one category-scoped exception SHALL exist: an ACTIVE skill in `SkillCategory.DIVINE_MYSTERY`
additionally passes a per-world-calendar-day claim before accruing. That rule and its scenarios are
owned by the `divine-mystery` capability and SHALL NOT be restated here; no other category carries a
cadence of any kind.

#### Scenario: A physical skill accrues like a spell
- **WHEN** an ACTIVE sword skill resolves successfully for an elf (learning x10) with no affinity and no growth buff
- **THEN** `db.skill_proficiency[skill_key]` increases by exactly `SKILL_PRACTICE_XP_PER_USE × 10.0`

#### Scenario: The affinity multiplier participates
- **WHEN** an entity with `affinity_elements == ["fire"]` successfully casts a magic fire spell
- **THEN** the accrued XP carries the `1.1` factor; a non-favored element carries `0.9`, and a
  physical skill carrying `element == fire` carries `1.0`

#### Scenario: An elementless skill carries the neutral factor
- **WHEN** an entity with declared affinities successfully resolves a physical skill that declares no
  element, and a control entity with no declared affinities resolves the same skill
- **THEN** both accruals carry the `1.0` factor and neither entity's affinity set is read as a bonus
  or a penalty

#### Scenario: The conferred growth buff participates
- **WHEN** an entity with an active `conferred_growth_rate` buff successfully uses a skill
- **THEN** the accrued XP equals the base formula multiplied by `growth_rate_multiplier(entity)`

#### Scenario: An owned scoped growth skill accelerates only its own tree
- **WHEN** an entity owning a passive that declares a `growth_rate` effect scoped to one element
  successfully casts a magic spell of that element, and separately casts a magic spell of another
  element
- **THEN** the first accrual carries the declared multiplier and the second carries `1.0`

#### Scenario: An owned scoped growth skill leaves non-elemental practice alone
- **WHEN** an entity owning a scoped `growth_rate` passive successfully resolves a skill that
  declares no element
- **THEN** the accrual carries the `1.0` owned-skill factor

#### Scenario: The owned-skill and conferred factors multiply independently
- **WHEN** an entity owning a scoped `growth_rate` passive, and also carrying an active
  `conferred_growth_rate` buff, practises a skill of the scoped element
- **THEN** the accrued XP carries both factors multiplied together

#### Scenario: A PASSIVE skill never accrues
- **WHEN** any game event touches a PASSIVE skill of the actor
- **THEN** `db.skill_proficiency` gains nothing for that key

#### Scenario: Rolled-back resolutions restore proficiency
- **WHEN** a successful resolution's later pending effect fails and the action snapshot restores
- **THEN** `db.skill_proficiency` is byte-equal to its pre-action value

#### Scenario: A non-divine category carries no daily brake
- **WHEN** an ACTIVE skill outside `SkillCategory.DIVINE_MYSTERY` resolves successfully many times
  across one world-calendar day on distinct ticks
- **THEN** every resolution accrues, because the cadence applies to that one category only
