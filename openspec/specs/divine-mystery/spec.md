## Purpose

Defines the 神之秘法 (Divine Mystery) skill family: which skills belong to it, how they are gated by
race, and how the unmechanized mysteries are declared as deliberately inert flavor entries rather
than silently missing content.

## Requirements

### Requirement: Divine Mystery skills are gated by RaceProfile.can_use_divine_arts
The six 神之秘法 family skills (`divine_sexual_mastery`, `divine_sexual_arts`, and the four
unmechanized mysteries) SHALL declare `SkillDef.requires_divine_arts=True` and be ownable/castable
only by an entity whose race's `RaceProfile.can_use_divine_arts` is `True`. Skills without the marker
(including the generic `sexual_event` mechanism) SHALL NOT be race-gated by this change. This
change SHALL NOT modify `can_use_divine_arts` itself or its existing per-race values — it only adds
consumers gated by the already-landed field.

#### Scenario: A non-elf cannot cast a Divine Mystery skill even if granted ownership
- **WHEN** a `human` or `beastfolk` entity somehow owns `divine_sexual_arts`
- **THEN** casting it is rejected, since `RACE_REGISTRY["human"].can_use_divine_arts` and
  `RACE_REGISTRY["beastfolk"].can_use_divine_arts` are both `False`

#### Scenario: An elf can cast divine_sexual_arts at no MP/SP cost
- **WHEN** an elf entity owning `divine_sexual_arts` casts it at a valid target whose resist contest
  resolves `resisted=False`
- **THEN** the cast is not rejected for insufficient MP or SP (the skill's `cost` is empty), and it
  resolves via the `sexual_event_target:` effect handler against the surviving target

#### Scenario: The integrated act's gate order is race first, then resist
- **WHEN** a non-divine-capable actor owning `divine_sexual_arts` casts it at a valid target
- **THEN** `_step1_divine_arts_gate` rejects the cast before any resist contest runs, exactly as for
  the `divine.py` acts

### Requirement: Divine Mystery practice accrues at most once per world-calendar day
Resolution practice accrual for an ACTIVE skill whose `SkillCategory` is `DIVINE_MYSTERY` SHALL be
claimed per actor, per skill, per world-calendar day: the first use-driven accrual of a calendar day
awards normally and every further use-driven accrual of that same skill on that same day SHALL award
nothing and report that nothing was claimed. The cadence governs the use-driven resolution pathway
only; declared booked practice (`grant_study_practice_xp`) is not a use and accrues exactly as it
does today. The calendar day SHALL be derived from the world clock's own calendar constants, never
from wall-clock time. The claim SHALL be scoped by skill category only; a skill that declares
`requires_divine_arts` but is NOT in the `DIVINE_MYSTERY` category SHALL accrue exactly as it does
today. The claim SHALL be persisted on the actor and SHALL be restored together with the actor's
proficiency when a resolution is rolled back, so a failed commit never consumes a day. The cadence
SHALL be evaluated before the per-world-clock-tick dedupe claim, so a day-blocked use takes no tick
claim.

#### Scenario: A second use of the same mystery on the same day accrues nothing
- **WHEN** an actor successfully resolves the same `DIVINE_MYSTERY` skill twice on the same
  world-calendar day, against targets and ticks that the per-tick dedupe would otherwise allow
- **THEN** `db.skill_proficiency[skill_key]` reflects exactly one accrual

#### Scenario: The next calendar day accrues again
- **WHEN** the world clock has advanced into the following calendar day and the actor resolves the
  same `DIVINE_MYSTERY` skill again
- **THEN** a second accrual is awarded

#### Scenario: Each mystery holds its own day
- **WHEN** an actor resolves two different `DIVINE_MYSTERY` skills on the same calendar day
- **THEN** both accrue, because the claim is keyed by skill as well as by day

#### Scenario: A divine-arts skill outside the category is unaffected
- **WHEN** an actor resolves a skill that declares `requires_divine_arts=True` but whose category is
  not `DIVINE_MYSTERY` (the 情慾秘術 divine line) twice on one calendar day, on distinct ticks
- **THEN** both resolutions accrue, exactly as before this change

#### Scenario: A rolled-back resolution does not consume the day
- **WHEN** a `DIVINE_MYSTERY` resolution accrues and a later pending effect of the same action fails,
  restoring the action snapshot
- **THEN** the actor's persisted day claim is byte-equal to its pre-action value, and a retry on the
  same day accrues normally

#### Scenario: A day-blocked use takes no per-tick claim
- **WHEN** a `DIVINE_MYSTERY` accrual is refused because the day is already claimed
- **THEN** no `(actor, skill, target)` entry for that call appears in the per-tick dedupe claim set

### Requirement: The divine-mystery family takes no element verb and costs nothing
Every skill in `SkillCategory.DIVINE_MYSTERY` SHALL declare an empty resource cost, SHALL declare
`requires_divine_arts=True`, and SHALL NOT declare any damage or healing effect. The family's effects
SHALL come only from the conferral, revocation, veil and reveal vocabulary — the layer that rewrites who
holds a power, who can see a fact, and how fast someone learns — so the family never supplies, and never
competes with, a combat verb an element tree owns. This is a family-wide invariant that any future node
added to the category SHALL also satisfy.

#### Scenario: No divine-mystery skill carries a cost
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** each declares an empty `cost` mapping

#### Scenario: No divine-mystery skill deals damage or heals
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** none declares a damage or healing effect

#### Scenario: Every divine-mystery skill is bloodline-gated
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** each declares `requires_divine_arts=True`, so a race without divine affinity is refused at
  cast time by the shipped gate

#### Scenario: A race without divine affinity cannot cast any of them
- **WHEN** an entity of a race whose profile reports no divine affinity somehow owns a
  `DIVINE_MYSTERY` skill and casts it
- **THEN** the cast is rejected by the bloodline gate before any resource, roll or effect resolution

### Requirement: Divine-mystery progression composes conferral, veil and reveal behavior
A divine-mystery chain SHALL compose into executable behavior, not into declared-but-inert entries: a
later rung of a conferral chain SHALL produce a strictly larger conferred effect on its target than an
earlier rung of the same chain; a conferral node declaring an ally audience SHALL reach every ally in
the resolved audience rather than only the selected target; and a node declaring several parents SHALL
stay unusable until EVERY declared parent meets its threshold, becoming usable when the last one does.
These contracts SHALL be established over synthetic compositions rather than by restating the shipped
catalog's rows.

#### Scenario: A later rung confers more than an earlier rung
- **WHEN** the same caster confers through an earlier-rung node and then through a later-rung node of
  the same chain onto the same target
- **THEN** the target's resulting effective value is strictly larger after the later rung

#### Scenario: An ally-audience conferral reaches the whole party
- **WHEN** a conferral node declaring an ally audience resolves with several allies in the resolved
  audience
- **THEN** every ally in that audience holds the grant, not only the selected target

#### Scenario: A multi-parent capstone waits for its last parent
- **WHEN** a node declaring three parents has two of them at their thresholds and the third below
- **THEN** the node is not usable, and it becomes usable as soon as the third parent reaches its
  threshold

#### Scenario: A chain root is usable with no prerequisite
- **WHEN** an entity owns a chain-root divine-mystery node and none of its descendants
- **THEN** the root is usable, because a root declares no prerequisite edge
