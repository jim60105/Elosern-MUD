# Spec Delta

## MODIFIED Requirements

### Requirement: Successful ACTIVE resolution accruses lineage practice XP
Successful ACTIVE resolution SHALL award practice XP atomically from the configured base and independent race, affinity, conferred-growth and owned scoped-growth factors; affinity and owned elemental growth SHALL apply to registered elemental-magic learning, including damage-free spells, while other domains remain neutral and PASSIVE skills earn no XP.

#### Scenario: A physical skill accrues like a spell
- **WHEN** an ACTIVE sword skill resolves successfully for a fixed synthetic race (learning x2) with no affinity and no growth buff
- **THEN** `db.skill_proficiency[skill_key]` increases by exactly `SKILL_PRACTICE_XP_PER_USE × 2.0`

#### Scenario: The affinity multiplier participates
- **WHEN** an entity with `affinity_elements == ["t_element"]` successfully casts a fixed synthetic elemental-magic spell
- **THEN** the accrued XP carries a synthetic configured `1.25` factor; a non-favored element carries the synthetic configured `0.75` factor, and a
  physical skill carrying `element == t_element` carries `1.0`

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

#### Scenario: The owned-skill growth factor is defined
- **WHEN** the owned-skill growth factor is computed for a practised skill
- **THEN** it is the product of the multipliers of every eligible owned scoped `growth_rate` effect carried by a
  skill the actor OWNS whose declared scope equals the element of the skill being practised, and
  `1.0` for a skill of any other element, a skill outside elemental magic and a skill declaring no element, so an unscoped
  acceleration is not expressible

#### Scenario: Neither growth factor reads the other
- **WHEN** the owned-skill growth factor and `growth_rate_multiplier(entity)` (the conferred-buff
  pull path) are both in play
- **THEN** the two factors are independent; they multiply, and neither reads the other

#### Scenario: The affinity factor is magic-damage-scoped
- **WHEN** affinity and owned scoped growth are evaluated for a synthetic ACTIVE elemental-magic skill with a registered element
- **THEN** both use that element regardless of damage, healing, buff, control, cleanse or mixed effects; elemental-tagged physical martial skills and other learning domains use neutral elemental factors

#### Scenario: Storage and derivation are unchanged
- **WHEN** practice XP accrues
- **THEN** it lands in `db.skill_proficiency[skill_key]` as float XP with `level = floor(xp / configured_xp_per_level)`

#### Scenario: A simulated resolution accrues nothing
- **WHEN** a resolution carries the simulated marker (a guild examination's
  `event_context["simulated"]`)
- **THEN** it accrues nothing

#### Scenario: Accrual ignores school and stats
- **WHEN** any accrual is computed
- **THEN** it reads neither the actor's school nor any magic stat

#### Scenario: The one divine cadence exception
- **WHEN** an ACTIVE skill in `SkillCategory.DIVINE_MYSTERY` resolves successfully; the exactly one
  category-scoped exception that additionally passes a per-world-calendar-day claim before accruing
- **THEN** that rule and its scenarios are owned by the `divine-mystery` capability and SHALL NOT be
  restated here; no other category carries a cadence of any kind

#### Scenario: Damage-free magic shares both award paths
- **WHEN** synthetic elemental healing, self-buff and control skills are practised through successful use and booked study
- **THEN** both paths apply the same affinity and owned scoped-growth eligibility, retaining their independently configured base amounts and caps

#### Scenario: Learning modifiers change XP alone
- **WHEN** the same synthetic eligible spell is resolved with different elemental affinity or owned scoped-growth factors
- **THEN** XP changes by those factors while innate bases, resolved damage/heal output and MP charge remain unchanged

#### Scenario: No declared affinity remains neutral
- **WHEN** a synthetic learner has no declared elemental affinity
- **THEN** the affinity factor is neutral for each eligible elemental skill, with owned scoped growth evaluated independently
