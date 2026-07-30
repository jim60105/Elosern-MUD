## ADDED Requirements

### Requirement: monster_behaviour_policy is a complete, drop-in action_provider
`world/rules/monster_behaviour.py` SHALL provide `monster_behaviour_policy(entity, battlefield) ->
ActionRequest | None`, callable anywhere change 9's `default_attack_policy` is callable — as the
`action_provider` argument to `world.rules.combat.run_round()`/`run_battle()` and
`world.rules.overwhelm.resolve_overwhelm()` — with no modification to either module's code.

#### Scenario: The function is a valid action_provider for run_round
- **WHEN** `combat.run_round(battlefield, monster_behaviour_policy)` is called on a battlefield
  containing at least one living `Monster` with a valid target and owned damage skill
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
`world/rules/monster_behaviour.py` SHALL select a single target by the acting monster's
`BehaviourProfile.target_strategy` — `"lowest_hp"` (current `hp.value`) or
`"highest_effective_power"` (change 9's `effective_power()`) — breaking an exact tie by drawing from
`dice.roll_d100()`, never Python's `random` module directly.

#### Scenario: lowest_hp strategy selects the enemy with the least current hp
- **WHEN** target selection runs with `target_strategy: lowest_hp` against a set of living enemies with
  distinct `hp.value`s
- **THEN** the enemy with the smallest `hp.value` is selected

#### Scenario: highest_effective_power strategy selects the enemy with the greatest effective_power
- **WHEN** target selection runs with `target_strategy: highest_effective_power` against a set of living
  enemies with distinct `effective_power()` values
- **THEN** the enemy with the greatest `combat.effective_power()` value is selected

#### Scenario: An exact tie is broken by a seeded roll, reproducibly
- **WHEN** target selection runs against two enemies with exactly equal values under the active
  strategy's metric, under a fixed RNG seed
- **THEN** the same enemy is selected every time the identical seed and battlefield state are replayed,
  and the selection is made via a call to `dice.roll_d100()`, not `random.choice()` or equivalent

#### Scenario: No target selection call reads combat_modifiers or rolls outside dice.roll_d100
- **WHEN** `_choose_target()`'s implementation is inspected
- **THEN** the only randomness source it references is `world.rules.dice.roll_d100()`

### Requirement: Skill selection differs by archetype, comparing owned skills by a dice-free expected
damage estimate when configured to
`world/rules/monster_behaviour.py` SHALL select one owned `ACTIVE` skill whose `effects` include a
`damage:`-prefixed ID, filtered to `TargetSpec.SINGLE` or `TargetSpec.AREA` per the decided action
shape, using the acting monster's `BehaviourProfile.skill_choice` — `"first_owned"` (no comparison) or
`"highest_expected_damage"` (compares `SkillHandler.effective_value()` for the skill's attacking stat,
minus the chosen target's `effective_value("defense")` when a single target is already known) — again
breaking an exact tie via `dice.roll_d100()`.

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

#### Scenario: Skill-choice comparison never rolls dice
- **WHEN** `_choose_skill()`'s implementation is inspected
- **THEN** it contains no call to `dice.roll_d100()` except inside its own tie-break branch, and no call
  to `ActionResolver.resolve()` or any effect-handler function — the actual to-hit and damage rolls
  happen only once resolution is invoked on the returned `ActionRequest`

### Requirement: Area-versus-single-target shape is decided before target/skill selection, reusing the
existing all-enemies shorthand
`world/rules/monster_behaviour.py` SHALL decide whether the acting monster uses an `AREA`-targeted or
`SINGLE`-targeted skill this turn based on `BehaviourProfile.prefer_area_when_multiple_enemies`, the
count of living enemies, and which target-spec shapes the entity owns a matching damage skill for, before
running target selection. An `AREA` decision SHALL use the `"all-enemies"` shorthand as its `targets`
value rather than computing an explicit target list. This decision SHALL only be reached when the flee
check (below) has not already returned a `flee` `ActionRequest` for the acting monster this turn.

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

### Requirement: A flee decision is evaluated before the area-versus-single decision, per archetype threshold
`world/rules/monster_behaviour.py` SHALL check, before deciding single-vs-area targeting, whether the
acting monster's `BehaviourProfile.flee_hp_fraction` is not `None` and the entity's current `hp.value /
hp.max` is at or below that fraction. When both hold, `monster_behaviour_policy()` SHALL return an
`ActionRequest` invoking change 10c's innately-owned `flee` skill (`skill_key` equal to
`world.rules.disengage.FLEE_SKILL_KEY`), targeting the acting entity itself, with a
`BattlefieldActionContext` whose `event_context` contains `{"battlefield": battlefield}`, and SHALL NOT
proceed to any target/skill selection for that turn. This check SHALL be stateless: it SHALL read only
the entity's current hp and its resolved `BehaviourProfile`, with no persistent record of a prior flee
attempt this encounter.

#### Scenario: A monster at or below its flee threshold attempts to flee instead of attacking
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for a `Monster` whose
  `hp.value / hp.max` is at or below its resolved `BehaviourProfile.flee_hp_fraction`
- **THEN** the returned `ActionRequest` has `skill_key == disengage.FLEE_SKILL_KEY`, `targets == [entity]`,
  and a `context` whose `event_context == {"battlefield": battlefield}`

#### Scenario: A monster above its flee threshold does not attempt to flee
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for a `Monster` whose
  `hp.value / hp.max` is strictly above its resolved `BehaviourProfile.flee_hp_fraction`
- **THEN** the returned `ActionRequest`, if any, does not name `disengage.FLEE_SKILL_KEY` as its
  `skill_key`

#### Scenario: An archetype with flee_hp_fraction: None never attempts to flee regardless of hp
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for a `Monster` whose resolved
  `BehaviourProfile.flee_hp_fraction` is `None`, at any current hp fraction including a value approaching
  `0`
- **THEN** the returned `ActionRequest` never names `disengage.FLEE_SKILL_KEY` as its `skill_key`

#### Scenario: The flee check is stateless and re-evaluated fresh every turn
- **WHEN** `monster_behaviour_policy(entity, battlefield)` is called for the same `Monster` on two
  consecutive turns, its hp fraction remaining at or below its flee threshold on both calls, with no
  intervening change to `battlefield.fled`
- **THEN** both calls return a `flee` `ActionRequest` — the function retains no memory of the first
  call's outcome and does not suppress or alter the second call's decision based on it

#### Scenario: A successful or failed flee attempt is resolved entirely through ActionResolver
- **WHEN** the `ActionRequest` returned by the flee branch is passed to `ActionResolver.resolve()`
- **THEN** resolution proceeds through change 8's unmodified pipeline and change 10c's `disengage` effect
  handler with no other code path in `world/rules/monster_behaviour.py` involved in determining success
  or writing to `battlefield.fled`

#### Scenario: The flee branch works unmodified inside change 10's compressed loop
- **WHEN** `overwhelm.resolve_overwhelm(battlefield, monster_behaviour_policy, max_rounds)` is called on a
  battlefield containing a `Monster` at or below its flee threshold
- **THEN** the call completes without stalling or requiring interactive input, and a successful flee
  during that resolution results in the fleeing entity's key appearing in `battlefield.fled` by the time
  `resolve_overwhelm()` returns

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

### Requirement: Golden fixed-seed tests demonstrate each archetype's flee threshold firing at the right
boundary and not above it
`world/rules/tests/` SHALL contain, for each of the four `MonsterTier` default archetypes, a fixed-seed
golden test asserting `monster_behaviour_policy()` returns a `flee` `ActionRequest` when the monster's hp
fraction is at or below that archetype's `flee_hp_fraction`, and does not when the hp fraction is set
just above it — with the `apex_predator` archetype asserted to never flee regardless of how low its hp
fraction is set.

#### Scenario: instinctive flees at its threshold and not just above it
- **WHEN** an `instinctive`-archetype `Monster`'s hp fraction is set to exactly its `flee_hp_fraction` and,
  separately, to a value one hp point above the fraction that would trigger it
- **THEN** the first case returns a `flee` `ActionRequest` and the second does not

#### Scenario: pack_hunter flees at its threshold and not just above it
- **WHEN** a `pack_hunter`-archetype `Monster`'s hp fraction is set to exactly its `flee_hp_fraction` and,
  separately, to a value one hp point above the fraction that would trigger it
- **THEN** the first case returns a `flee` `ActionRequest` and the second does not

#### Scenario: brute flees at its threshold and not just above it
- **WHEN** a `brute`-archetype `Monster`'s hp fraction is set to exactly its `flee_hp_fraction` and,
  separately, to a value one hp point above the fraction that would trigger it
- **THEN** the first case returns a `flee` `ActionRequest` and the second does not

#### Scenario: apex_predator never flees at any hp fraction
- **WHEN** an `apex_predator`-archetype `Monster`'s hp fraction is set to its tier's lowest plausible
  value (approaching `0`)
- **THEN** `monster_behaviour_policy()` does not return a `flee` `ActionRequest`, consistent with its
  `flee_hp_fraction` of `None`

#### Scenario: Each archetype's flee golden test is reproducible under its fixed seed
- **WHEN** each of the four archetypes' golden flee tests is run twice under its own fixed seed and
  identical starting state
- **THEN** the fire/no-fire outcome and the returned `ActionRequest` (when one is returned) are identical
  across both runs
