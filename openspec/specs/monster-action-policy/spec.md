## Purpose

Define deterministic, rulebook-driven monster combat decisions that produce
resolver-ready actions without mutating combat state.

## Requirements

### Requirement: monster_behaviour_policy is a complete, drop-in action_provider
`world/rules/monster_behaviour.py` SHALL provide `monster_behaviour_policy(entity, battlefield) ->
ActionRequest | None`, callable anywhere change 9's `default_attack_policy` is callable — as the
`action_provider` argument to `world.rules.combat.run_round()`/`run_battle()` and
`world.rules.overwhelm.resolve_overwhelm()` — with no modification to either module's code.

#### Scenario: The function is a valid action_provider for run_round
- **WHEN** `combat.run_round(battlefield, monster_behaviour_policy)` is called on a battlefield
  containing at least one living `Monster` with a valid target and affordable owned damage skill
- **THEN** the round completes, producing an `EventLog` for that `Monster`'s resolved action, with no
  change required to `world/rules/combat.py`

#### Scenario: The function is a valid action_provider for resolve_overwhelm
- **WHEN** `overwhelm.resolve_overwhelm(battlefield, monster_behaviour_policy, max_rounds)` is called on
  an overwhelm-classified battlefield involving at least one `Monster`
- **THEN** the call completes and returns an `OverwhelmResult` with no change required to
  `world/rules/overwhelm.py`, and no round takes materially longer to compute than an equivalent call
  using `default_attack_policy`

#### Scenario: Every decision is issued as a single ActionRequest through ActionResolver
- **WHEN** `monster_behaviour_policy(entity, battlefield)` returns a non-`None` value for any `Monster`
  and any owned-skill/target combination
- **THEN** the returned value is a single `ActionRequest` whose `context` is a
  `BattlefieldActionContext` wrapping the same `battlefield` argument, and resolving it calls
  `ActionResolver.resolve()` with no other code path applying an effect, deducting a resource, or
  emitting an `EventLog`

### Requirement: A monster with zero actions_per_turn is skipped by the existing gate, with no
monster-specific bypass
`world/rules/monster_behaviour.py` SHALL contain no reference to `combat_modifiers`,
`evaluate_combat_modifiers`, `actions_per_turn`, `entity.buffs`, or `entity.sexual` anywhere in its
source — the zeroed-actions gate belongs entirely to change 9's `run_round()`, which already skips a
combatant's turn before calling `action_provider` at all.

#### Scenario: monster_behaviour_policy is never called for a zeroed-actions combatant
- **WHEN** `run_round(battlefield, monster_behaviour_policy)` processes a `Monster` for whom
  `evaluate_combat_modifiers(entity)` returns `{"actions_per_turn": 0}`
- **THEN** `monster_behaviour_policy` is not invoked for that combatant this round, and the round's
  event list contains an `"action_skipped"` entry naming that combatant instead

#### Scenario: No source-level reference to combat-modifier or sexual-state concepts
- **WHEN** `world/rules/monster_behaviour.py`'s source is inspected
- **THEN** it contains no token matching `combat_modifiers`, `evaluate_combat_modifiers`,
  `actions_per_turn`, `entity.buffs`, or `entity.sexual`

### Requirement: No LLM or generative-layer involvement anywhere in monster decision-making
`world/rules/monster_behaviour.py` SHALL import nothing from `world/ai/`, SHALL make no network call,
and every decision it produces SHALL be a pure function of `entity`/`battlefield` state plus
`MONSTER_BEHAVIOUR_YAML` and change 9's seeded `dice.roll_d100()`.

#### Scenario: A source scan finds no generative-layer import
- **WHEN** `world/rules/monster_behaviour.py` is scanned for any `import` statement referencing
  `world.ai` or an LLM-client module
- **THEN** none is found

#### Scenario: Repeated calls under an unchanged battlefield and RNG state produce the same decision
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called twice in immediate succession with
  no intervening `roll_d100()` call and no change to `entity`'s or `battlefield`'s state
- **THEN** both calls return an `ActionRequest` naming the identical `skill_key` and the identical
  target(s)

### Requirement: Target selection differs by archetype and is deterministic under a fixed seed
`world/rules/monster_behaviour.py` SHALL select a single target by the acting monster's `BehaviourProfile.target_strategy` — `"lowest_hp"` (current `hp.value`) or `"highest_effective_power"` (change 9's `effective_power()`) — breaking an exact tie by drawing from `dice.roll_d100()`, never Python's `random` module directly.

#### Scenario: lowest_hp strategy selects the enemy with the least current hp
- **WHEN** target selection runs with `target_strategy: lowest_hp` against a set of living enemies with distinct `hp.value`s
- **THEN** the enemy with the smallest `hp.value` is selected

#### Scenario: highest_effective_power strategy selects the enemy with the greatest effective_power
- **WHEN** target selection runs with `target_strategy: highest_effective_power` against a set of living enemies with distinct `effective_power()` values
- **THEN** the enemy with the greatest `combat.effective_power()` value is selected

#### Scenario: An exact tie is broken by a seeded roll, reproducibly
- **WHEN** target selection runs against two enemies with exactly equal values under the active strategy's metric, under a fixed RNG seed
- **THEN** the same enemy is selected every time the identical seed and battlefield state are replayed, and the selection is made via a call to `dice.roll_d100()`, not `random.choice()` or equivalent

#### Scenario: Displaced enemies leave the strike-class candidate set without extra dice
- **WHEN** a strike-class-only monster's target selection runs against one displaced and one undisplaced living enemy under a fixed seed, and separately against a set where every living enemy is displaced, and separately a magic-owning caster monster selects against the same mixed set
- **THEN** the first case selects the undisplaced enemy with no additional randomness draw beyond the shipped tie-break path, the second case yields no action request, and the caster monster's magic-school single-target selection keeps the displaced candidate reachable — replaying the identical seed and state reproduces every outcome

#### Scenario: No target selection call reads combat_modifiers or rolls outside dice.roll_d100
- **WHEN** `_choose_target()`'s implementation is inspected
- **THEN** the only randomness source it references is `world.rules.dice.roll_d100()`

#### Scenario: Strike-class SINGLE candidate set excludes displaced enemies
- **WHEN** a STRIKE-class (physical-school damage) SINGLE-target selection computes its candidate set
- **THEN** the set excludes enemies holding a live positional-marker instance (state-only, dice-free
  — the same metric and tie-break machinery applies to the remaining candidates)

#### Scenario: The exclusion applies at candidate selection for strike-only kits
- **WHEN** skill choice can follow target choice and the acting monster's owned SINGLE-target damage
  kit is exclusively strike-class
- **THEN** the positional exclusion is applied at candidate selection

#### Scenario: Magic SINGLE kits may keep displaced candidates
- **WHEN** the acting monster owns a magic-school SINGLE-target damage skill
- **THEN** it MAY keep displaced candidates for that magic kit (magic reachability is ratified
  unaffected; the step-4a resolution gate remains the sole authority for strike-class pairings)

#### Scenario: No reachable kit yields no action this round
- **WHEN** the strike-class candidate set is empty while the actor holds no reachable magic SINGLE kit
- **THEN** the policy returns no action for this round, deterministic and reproducible under a fixed
  seed exactly like the no-living-enemies case

#### Scenario: The AREA shorthand candidate set keeps displaced enemies
- **WHEN** the AREA shorthand candidate set is computed
- **THEN** it keeps displaced candidates (area reachability is unaffected)

#### Scenario: The delegated policy applies the identical positional exclusion
- **WHEN** the delegated `default_attack_policy` computes its strike-class candidate set
- **THEN** it applies the identical positional exclusion

### Requirement: Skill selection differs by archetype, comparing owned skills by a dice-free expected
damage estimate when configured to
`world/rules/monster_behaviour.py` SHALL select one affordable owned `ACTIVE` skill passing shared identity and prerequisite qualification whose `effects`
include a `damage:`-prefixed ID, filtered to `TargetSpec.SINGLE` or `TargetSpec.AREA` per the decided
action shape, using the acting monster's `BehaviourProfile.skill_choice`, `"first_owned"` (no
comparison) or `"highest_expected_damage"`.

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

### Requirement: Highest-expected-damage comparison uses effective value and one tie-breaking roll
The `"highest_expected_damage"` comparison SHALL compare `SkillHandler.effective_value()` for the skill's
attacking stat, and an exact tie SHALL be broken via one `dice.roll_d100()` roll.

#### Scenario: The comparison stat and the single tie-break roll
- **WHEN** `"highest_expected_damage"` compares two eligible owned skills and their estimates are exactly equal
- **THEN** the greater `effective_value(attacking_stat)` is selected, and only an exact tie consumes one
  `dice.roll_d100()` roll

### Requirement: Area-versus-single-target shape is decided before target/skill selection, reusing the
existing all-enemies shorthand
`world/rules/monster_behaviour.py` SHALL decide whether the acting monster uses an `AREA`-targeted or
`SINGLE`-targeted skill this turn based on `BehaviourProfile.prefer_area_when_multiple_enemies`, the
count of living enemies, and which target-spec shapes the entity owns a matching damage skill for, before
running target selection. An `AREA` decision SHALL use the `"all-enemies"` shorthand as its `targets`
value rather than computing an explicit target list.

#### Scenario: An archetype preferring area skills uses one when multiple enemies are present
- **WHEN** the acting monster's profile has `prefer_area_when_multiple_enemies: true`, more than one
  living enemy is present, and the entity owns at least one `TargetSpec.AREA` damage skill
- **THEN** the returned `ActionRequest`'s `targets` is the string `"all-enemies"` and its `skill_key`
  names an owned `AREA` damage skill

#### Scenario: A single living enemy never triggers the area branch
- **WHEN** the acting monster's profile has `prefer_area_when_multiple_enemies: true` but only one
  living enemy remains
- **THEN** the returned `ActionRequest` targets that single enemy explicitly via a `SINGLE` damage skill,
  not the `"all-enemies"` shorthand

#### Scenario: An archetype not preferring area still falls back to it if no single-target skill exists
- **WHEN** the acting monster's profile has `prefer_area_when_multiple_enemies: false` and the entity
  owns only `TargetSpec.AREA` damage skills, no `TargetSpec.SINGLE` ones
- **THEN** the returned `ActionRequest` still uses the owned `AREA` skill against `"all-enemies"` rather
  than returning `None`

#### Scenario: An entity owning no eligible damage skill of either shape returns None
- **WHEN** the acting `Monster` owns no `ACTIVE` skill whose `effects` include a `damage:`-prefixed ID
- **THEN** `monster_behaviour_policy()` returns `None`, identically to change 9's own
  `default_attack_policy` behaviour for the same condition

### Requirement: A non-Monster entity is delegated to change 9's default_attack_policy unmodified
`monster_behaviour_policy(entity, battlefield)` SHALL detect whether `entity` is a `Monster` by checking
for a `threat_tier` attribute, and SHALL delegate entirely to
`world.rules.combat.default_attack_policy(entity, battlefield)` for any entity lacking one, with no
difference in outcome from calling `default_attack_policy` directly.

#### Scenario: A PlayerCharacter or NPC entity produces the identical decision as default_attack_policy
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for an entity with no `threat_tier`
  attribute
- **THEN** it returns the exact same value `combat.default_attack_policy(entity, battlefield)` would
  return for the identical arguments

#### Scenario: A Monster entity never falls through to the delegation branch
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for an entity with a `threat_tier`
  attribute
- **THEN** `combat.default_attack_policy` is not called at all for that turn

### Requirement: Golden fixed-seed tests demonstrate distinct, reproducible behaviour across MonsterTiers
`world/rules/tests/` SHALL contain a fixed-seed golden test constructing an identical battlefield (same
enemy roster and stats) faced by one monster from each of the four `MonsterTier` defaults, asserting
that at least the `low` and `calamity` tier monsters make different target choices on that identical
roster, and that every choice is exactly reproducible under the fixture's seed.

#### Scenario: Low-tier and calamity-tier monsters choose different targets on an identical roster
- **WHEN** the golden fixture's enemy roster contains one low-current-hp, low-`effective_power()` enemy
  and one high-current-hp, high-`effective_power()` enemy, and both a `low`-tier-default and a
  `calamity`-tier-default `Monster` face that identical roster under the same fixed seed
- **THEN** the `low`-tier monster's `monster_behaviour_policy()` output targets the low-hp enemy and the
  `calamity`-tier monster's output targets the high-power enemy

#### Scenario: The golden fixture's decisions are byte-identical across repeated runs under the same seed
- **WHEN** the golden fixture is run twice under the identical fixed seed and starting battlefield state
- **THEN** every `ActionRequest` `monster_behaviour_policy()` produces across both runs is identical in
  `skill_key` and `targets`

### Requirement: A delegated non-Monster entity proposes the first usable resolver-backed damage skill
`world/rules/combat.py`'s `default_attack_policy(entity, battlefield)` SHALL consider every owned
`ACTIVE` skill with a `damage:`-prefixed effect and select the first one `ActionResolver` can
resolve — ownership, prerequisite satisfaction via `can_use_skill`, and MP affordability are the
eligibility gates.

#### Scenario: A prerequisite-unsatisfied spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  affordable `firestorm` whose `scorching_wave` prerequisite is below the edge threshold — and a
  living enemy is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  gated spell, and `ActionResolver` accepts the request

#### Scenario: An unaffordable spell falls back to the innate basic_attack
- **WHEN** `default_attack_policy` runs for a non-Monster entity (e.g. a party NPC) that owns an
  elemental spell it cannot afford — `skills=["firestorm"]`, `mp < 30` — and a living enemy
  is present
- **THEN** the returned `ActionRequest` names `"basic_attack"` targeting that enemy, never the
  unaffordable spell, and `ActionResolver` accepts the request

#### Scenario: A usable owned spell is chosen ahead of the innate
- **WHEN** the entity owns an affordable damage spell earlier in `owned_keys()` order than the innate
  skills, and its prerequisites are satisfied
- **THEN** `default_attack_policy` returns an `ActionRequest` naming that spell, because it passes
  `can_use_skill` and affordability

#### Scenario: A companion with only an unaffordable spell still acts every round
- **WHEN** a party NPC owning only the unaffordable `firestorm` (plus the innate skills) fights
  through `combat.run_round` against a living enemy
- **THEN** every round the NPC's resolved `basic_attack` action produces an `EventLog` entry — no
  round silently discards a rejected request and no `action_skipped` entry is emitted for a castable
  entity

#### Scenario: Resolver-rejected skills are skipped, never proposed
- **WHEN** a candidate skill would be rejected by the resolver (prerequisite-unsatisfied per
  `can_use_skill`, unowned, or MP-unaffordable for the current gauge)
- **THEN** it is skipped in favor of the next candidate — in practice the innate `basic_attack`,
  which is always affordable — and never proposed in an `ActionRequest` that `ActionResolver`
  rejects

#### Scenario: A malformed spell never raises the policy
- **WHEN** `default_attack_policy` encounters a malformed spell
- **THEN** the policy does not raise

### Requirement: Authored crocodile behavior uses the existing first-owned strategy
The crocodile kit SHALL bind a reusable existing-vocabulary profile using first-owned skill choice, lowest-current-HP targets, no area preference and the authored flee fraction. The bite SHALL precede innate attack. Ineligible or MP/SP-unaffordable bites SHALL fall back to an available ordinary attack.

#### Scenario: Resource exhaustion is ordinary fallback
- **WHEN** formal crocodile combat exhausts either payable bite resource
- **THEN** the next policy action resolves an ordinary attack without a new utility planner

#### Scenario: Current combat boundaries remain authoritative
- **WHEN** targets move, die or are knocked out before resolution or the crocodile reaches its flee threshold
- **THEN** existing close-range/displacement, living-target, knockout and flee rules apply; other profiles and target choices remain unchanged

### Requirement: 穗鳴雀 contact kit uses existing first-owned policy and fallback
Both variants SHALL bind `instinctive` with first-owned skill selection, lowest-current-HP targets, no area preference and the authored flee fraction. Affordable eligible `grain_shaking_peck` SHALL precede basic_attack; insufficient MP or SP SHALL fall back to ordinary attack without utility planning. Existing initiative-time resolver and target gates SHALL remain authoritative.

#### Scenario: Preferred skill and either exhaustion axis
- **WHEN** real sessions resolve an affordable special attack then separately exhaust MP and SP
- **THEN** the special action resolves first and each exhausted case resolves basic_attack next, without changing any other archetype or tier default

#### Scenario: Flee retains priority at its inclusive threshold
- **WHEN** a variant reaches its configured inclusive HP-fraction boundary with living enemies
- **THEN** the existing flee request precedes attack selection and uses the normal disengage resolver, with no teleportation or special burrow escape

#### Scenario: Targets and late state changes remain shared
- **WHEN** all valid enemies are displaced or eligibility/affordability changes after initiative
- **THEN** ordinary positional selection and final resolver gates apply with no creature-specific branch or new decision dice

### Requirement: 潮燈蟹 contact kit uses existing first-owned policy and fallback
Both variants SHALL bind `instinctive` with first-owned skill selection, lowest-current-HP targets, no area preference and the authored flee fraction. Affordable eligible `lamp_carapace_claw` SHALL precede basic_attack; insufficient MP or SP SHALL fall back to ordinary attack without utility planning. Existing initiative-time resolver and target gates SHALL remain authoritative.

#### Scenario: Preferred skill and either exhaustion axis
- **WHEN** real sessions resolve an affordable special attack then separately exhaust MP and SP
- **THEN** the special action resolves first and each exhausted case resolves basic_attack next, without changing any other archetype or tier default

#### Scenario: Flee retains priority at its inclusive threshold
- **WHEN** a variant reaches its configured inclusive HP-fraction boundary with living enemies
- **THEN** the existing flee request precedes attack selection and uses the normal disengage resolver, with no teleportation or special burrow escape

#### Scenario: Targets and late state changes remain shared
- **WHEN** all valid enemies are displaced or eligibility/affordability changes after initiative
- **THEN** ordinary positional selection and final resolver gates apply with no creature-specific branch or new decision dice

