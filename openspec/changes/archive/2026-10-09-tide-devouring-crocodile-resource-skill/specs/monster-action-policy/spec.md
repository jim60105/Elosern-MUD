# Spec Delta

## ADDED Requirements

### Requirement: Authored crocodile behavior uses the existing first-owned strategy
The crocodile kit SHALL bind a reusable existing-vocabulary profile using first-owned skill choice, lowest-current-HP targets, no area preference and flee fraction 0.20. The bite SHALL precede innate attack. Ineligible or MP/SP-unaffordable bites SHALL fall back to an available ordinary attack.

#### Scenario: Resource exhaustion is ordinary fallback
- **WHEN** formal crocodile combat exhausts either payable bite resource
- **THEN** the next policy action resolves an ordinary attack without a new utility planner

#### Scenario: Current combat boundaries remain authoritative
- **WHEN** targets move, die or are knocked out before resolution or the crocodile reaches its flee threshold
- **THEN** existing close-range/displacement, living-target, knockout and flee rules apply; other profiles and target choices remain unchanged

## MODIFIED Requirements

### Requirement: Skill selection differs by archetype, comparing owned skills by a dice-free expected
damage estimate when configured to
`world/rules/monster_behaviour.py` SHALL select one affordable owned `ACTIVE` skill passing shared identity and prerequisite qualification whose `effects`
include a `damage:`-prefixed ID, filtered to `TargetSpec.SINGLE` or `TargetSpec.AREA` per the decided
action shape, using the acting monster's `BehaviourProfile.skill_choice`, `"first_owned"` (no
comparison) or `"highest_expected_damage"` (compares `SkillHandler.effective_value()` for the skill's
attacking stat), breaking an exact tie via `dice.roll_d100()`.

#### Scenario: first_owned selects the first matching skill in the entity's own owned order
- **WHEN** skill selection runs with `skill_choice: first_owned` against an entity owning two or more
  eligible damage skills
- **THEN** the first one in `entity.skills.owned_keys()`'s order is selected, with no comparison of
  their attacking stats

#### Scenario: highest_expected_damage selects the skill with the greatest estimated output
- **WHEN** skill selection runs with `skill_choice: highest_expected_damage` against an entity owning
  two eligible damage skills with different `effective_value()` outputs for their respective attacking
  stats
- **THEN** the skill with the greater `effective_value(attacking_stat)` (adjusted by the target's
  `effective_value("defense")` for a `SINGLE`-shaped decision) is selected

#### Scenario: An unaffordable preferred skill falls back to an affordable damage skill
- **WHEN** a monster prefers an owned `AREA` damage skill but lacks its required resource and also owns
  an affordable `SINGLE` damage skill
- **THEN** the policy returns an `ActionRequest` for the affordable `SINGLE` skill instead of repeatedly
  returning a request that `ActionResolver` rejects for insufficient resources

#### Scenario: Skill-choice comparison never rolls dice
- **WHEN** `_choose_skill()`'s implementation is inspected
- **THEN** it contains no call to `dice.roll_d100()` except inside its own tie-break branch, and no call
  to `ActionResolver.resolve()` or any effect-handler function; the actual to-hit and damage rolls
  happen only once resolution is invoked on the returned `ActionRequest`

#### Scenario: The estimate subtracts the known target's defense
- **WHEN** `highest_expected_damage` compares skills and a single target is already known
- **THEN** each skill's estimate subtracts the chosen target's `effective_value("defense")`

#### Scenario: Affordability is evaluated before the area-versus-single decision
- **WHEN** the policy evaluates which target shape to commit to
- **THEN** affordability is evaluated before the area-versus-single decision, so an unavailable
  preferred shape can fall back to an affordable one

#### Scenario: Ineligible preferred skill falls back without rolling a cast
- **WHEN** the first owned damage skill fails shared identity or prerequisite eligibility and an ordinary attack is available
- **THEN** selection returns the available ordinary attack, while final resolution remains authoritative if initiative changes eligibility or affordability
