## ADDED Requirements

### Requirement: Divine Mystery practice accrues at most once per world-calendar day
Practice accrual for an ACTIVE skill whose `SkillCategory` is `DIVINE_MYSTERY` SHALL be claimed per
actor, per skill, per world-calendar day: the first accrual of a calendar day awards normally and
every further accrual of that same skill on that same day SHALL award nothing and report that nothing
was claimed. The calendar day SHALL be derived from the world clock's own calendar constants, never
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
