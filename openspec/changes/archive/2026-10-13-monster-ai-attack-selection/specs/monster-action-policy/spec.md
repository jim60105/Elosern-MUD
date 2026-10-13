## MODIFIED Requirements

### Requirement: monster_behaviour_policy is a complete, drop-in action_provider
The monster policy SHALL retain its two-argument ActionRequest-or-None provider contract for ordinary rounds, battles and overwhelm. Ephemeral execution identity and observation seams SHALL be permitted in round and overwhelm orchestration without changing initiative, damage or settlement authority.

#### Scenario: The function is a valid action_provider for run_round
- **WHEN** an ordinary round uses the monster provider
- **THEN** its selected action resolves once through the existing resolver with the real context and scope, including scale and target representation

#### Scenario: The function is a valid action_provider for resolve_overwhelm
- **WHEN** overwhelm resolves several rounds with repeated actor slots
- **THEN** each call has its actual round/slot scope and unchanged combat formulas; every action uses the existing resolver

#### Scenario: Every decision is issued as a single ActionRequest through ActionResolver
- **WHEN** a monster proposes a nonempty action in either mode
- **THEN** one request with the same battlefield context settles once through the resolver, which alone owns effects, resource payment and action events

### Requirement: A monster with zero actions_per_turn is skipped by the existing gate, with no
monster-specific bypass
The existing round capability gate SHALL skip zero-action monsters without invoking their provider. Utility read-only capability validation SHALL be permitted and SHALL NOT bypass the gate or create state.

#### Scenario: monster_behaviour_policy is never called for a zeroed-actions combatant
- **WHEN** a monster has zero permitted action opportunities
- **THEN** the provider is not called and the existing skipped-action event is produced

#### Scenario: No source-level reference to combat-modifier or sexual-state concepts
- **WHEN** utility is inspected directly for a zero-action monster
- **THEN** no illegal candidate is proposed and capability state remains unchanged

### Requirement: No LLM or generative-layer involvement anywhere in monster decision-making
Monster decisions SHALL execute offline without generative-layer or network involvement. Legacy SHALL use unchanged state, rulebook and combat-dice behavior. Utility SHALL use settled public snapshots, configuration, observations and independent scope-seeded selection RNG without hidden submissions.

#### Scenario: A source scan finds no generative-layer import
- **WHEN** external model and network access are disabled
- **THEN** valid monster decisions and resolver settlement still complete

#### Scenario: Repeated calls under an unchanged battlefield and RNG state produce the same decision
- **WHEN** identical state and RNG inputs are replayed for legacy, and identical state, observations, configuration and scope for utility
- **THEN** each mode repeats its action; utility does not change combat dice or depend on pending player intent

### Requirement: Target selection differs by archetype and is deterministic under a fixed seed
Legacy mode SHALL retain the following existing contract.
`world/rules/monster_behaviour.py` SHALL select a single target by the acting monster's `BehaviourProfile.target_strategy` ; `"lowest_hp"` (current `hp.value`) or `"highest_effective_power"` (change 9's `effective_power()`) ; breaking an exact tie by drawing from `dice.roll_d100()`, never Python's `random` module directly.

#### Scenario: lowest_hp strategy selects the enemy with the least current hp
- **WHEN** in legacy mode, target selection runs with `target_strategy: lowest_hp` against a set of living enemies with distinct `hp.value`s
- **THEN** the enemy with the smallest `hp.value` is selected

#### Scenario: highest_effective_power strategy selects the enemy with the greatest effective_power
- **WHEN** in legacy mode, target selection runs with `target_strategy: highest_effective_power` against a set of living enemies with distinct `effective_power()` values
- **THEN** the enemy with the greatest `combat.effective_power()` value is selected

#### Scenario: An exact tie is broken by a seeded roll, reproducibly
- **WHEN** in legacy mode, target selection runs against two enemies with exactly equal values under the active strategy's metric, under a fixed RNG seed
- **THEN** the same enemy is selected every time the identical seed and battlefield state are replayed, and the selection is made via a call to `dice.roll_d100()`, not `random.choice()` or equivalent

#### Scenario: Displaced enemies leave the strike-class candidate set without extra dice
- **WHEN** in legacy mode, a strike-class-only monster's target selection runs against one displaced and one undisplaced living enemy under a fixed seed, and separately against a set where every living enemy is displaced, and separately a magic-owning caster monster selects against the same mixed set
- **THEN** the first case selects the undisplaced enemy with no additional randomness draw beyond the shipped tie-break path, the second case yields no action request, and the caster monster's magic-school single-target selection keeps the displaced candidate reachable ; replaying the identical seed and state reproduces every outcome

#### Scenario: No target selection call reads combat_modifiers or rolls outside dice.roll_d100
- **WHEN** in legacy mode, targets tie under a fixed combat RNG seed
- **THEN** the chosen target and subsequent combat dice match the established sequence with no additional draws

#### Scenario: Strike-class SINGLE candidate set excludes displaced enemies
- **WHEN** in legacy mode, a STRIKE-class (physical-school damage) SINGLE-target selection computes its candidate set
- **THEN** the set excludes enemies holding a live positional-marker instance (state-only, dice-free
  ; the same metric and tie-break machinery applies to the remaining candidates)

#### Scenario: The exclusion applies at candidate selection for strike-only kits
- **WHEN** in legacy mode, skill choice can follow target choice and the acting monster's owned SINGLE-target damage
  kit is exclusively strike-class
- **THEN** the positional exclusion is applied at candidate selection

#### Scenario: Magic SINGLE kits may keep displaced candidates
- **WHEN** in legacy mode, the acting monster owns a magic-school SINGLE-target damage skill
- **THEN** it MAY keep displaced candidates for that magic kit (magic reachability is ratified
  unaffected; the step-4a resolution gate remains the sole authority for strike-class pairings)

#### Scenario: No reachable kit yields no action this round
- **WHEN** in legacy mode, the strike-class candidate set is empty while the actor holds no reachable magic SINGLE kit
- **THEN** the policy returns no action for this round, deterministic and reproducible under a fixed
  seed exactly like the no-living-enemies case

#### Scenario: The AREA shorthand candidate set keeps displaced enemies
- **WHEN** in legacy mode, the AREA shorthand candidate set is computed
- **THEN** it keeps displaced candidates (area reachability is unaffected)

#### Scenario: The delegated policy applies the identical positional exclusion
- **WHEN** in legacy mode, the delegated `default_attack_policy` computes its strike-class candidate set
- **THEN** it applies the identical positional exclusion

### Requirement: Skill selection differs by archetype, comparing owned skills by a dice-free expected
Legacy mode SHALL retain the following existing contract.
damage estimate when configured to
`world/rules/monster_behaviour.py` SHALL select one affordable owned `ACTIVE` skill passing shared identity and prerequisite qualification whose `effects`
include a `damage:`-prefixed ID, filtered to `TargetSpec.SINGLE` or `TargetSpec.AREA` per the decided
action shape, using the acting monster's `BehaviourProfile.skill_choice`, `"first_owned"` (no
comparison) or `"highest_expected_damage"`.

#### Scenario: first_owned selects the first matching skill in the entity's own owned order
- **WHEN** in legacy mode, skill selection runs with `skill_choice: first_owned` against an entity owning two or more
  eligible damage skills
- **THEN** the first one in `entity.skills.owned_keys()`'s order is selected, with no comparison of
  their attacking stats

#### Scenario: highest_expected_damage selects the skill with the greatest estimated output
- **WHEN** in legacy mode, skill selection runs with `skill_choice: highest_expected_damage` against an entity owning
  two eligible damage skills with different `effective_value()` outputs for their respective attacking
  stats
- **THEN** the skill with the greater `effective_value(attacking_stat)` (adjusted by the target's
  `effective_value("defense")` for a `SINGLE`-shaped decision) is selected

#### Scenario: An unaffordable preferred skill falls back to an affordable damage skill
- **WHEN** in legacy mode, a monster prefers an owned `AREA` damage skill but lacks its required resource and also owns
  an affordable `SINGLE` damage skill
- **THEN** the policy returns an `ActionRequest` for the affordable `SINGLE` skill instead of repeatedly
  returning a request that `ActionResolver` rejects for insufficient resources

#### Scenario: Skill-choice comparison never rolls dice
- **WHEN** in legacy mode, eligible skill estimates are distinct and separately tied
- **THEN** distinct comparison consumes no dice, the tied comparison consumes the existing single tie-break draw, and selection applies no effects or resource payment

#### Scenario: The estimate subtracts the known target's defense
- **WHEN** in legacy mode, `highest_expected_damage` compares skills and a single target is already known
- **THEN** each skill's estimate subtracts the chosen target's `effective_value("defense")`

#### Scenario: Affordability is evaluated before the area-versus-single decision
- **WHEN** in legacy mode, the policy evaluates which target shape to commit to
- **THEN** affordability is evaluated before the area-versus-single decision, so an unavailable
  preferred shape can fall back to an affordable one

#### Scenario: Ineligible preferred skill falls back without rolling a cast
- **WHEN** in legacy mode, the first owned damage skill fails shared identity or prerequisite eligibility and an ordinary attack is available
- **THEN** selection returns the available ordinary attack, while final resolution remains authoritative if initiative changes eligibility or affordability

### Requirement: Highest-expected-damage comparison uses effective value and one tie-breaking roll
Legacy mode SHALL retain the following existing contract.
The `"highest_expected_damage"` comparison SHALL compare `SkillHandler.effective_value()` for the skill's
attacking stat, and an exact tie SHALL be broken via one `dice.roll_d100()` roll.

#### Scenario: The comparison stat and the single tie-break roll
- **WHEN** in legacy mode, `"highest_expected_damage"` compares two eligible owned skills and their estimates are exactly equal
- **THEN** the greater `effective_value(attacking_stat)` is selected, and only an exact tie consumes one
  `dice.roll_d100()` roll

### Requirement: Area-versus-single-target shape is decided before target/skill selection, reusing the
Legacy mode SHALL retain the following existing contract.
`world/rules/monster_behaviour.py` SHALL decide whether the acting monster uses an `AREA`- or
`SINGLE`-targeted skill this turn from `BehaviourProfile.prefer_area_when_multiple_enemies`, the
count of living enemies, and which target-spec shapes the entity owns a matching damage skill for,
before target selection. An `AREA` decision SHALL use the `"all-enemies"` shorthand as `targets`
rather than an explicit target list.

#### Scenario: An archetype preferring area skills uses one when multiple enemies are present
- **WHEN** in legacy mode, the acting monster's profile has `prefer_area_when_multiple_enemies: true`, more than one
  living enemy is present, and the entity owns at least one `TargetSpec.AREA` damage skill
- **THEN** the returned `ActionRequest`'s `targets` is the string `"all-enemies"` and its `skill_key`
  names an owned `AREA` damage skill

#### Scenario: A single living enemy never triggers the area branch
- **WHEN** in legacy mode, the acting monster's profile has `prefer_area_when_multiple_enemies: true` but only one
  living enemy remains
- **THEN** the returned `ActionRequest` targets that single enemy explicitly via a `SINGLE` damage skill,
  not the `"all-enemies"` shorthand

#### Scenario: An archetype not preferring area still falls back to it if no single-target skill exists
- **WHEN** in legacy mode, the acting monster's profile has `prefer_area_when_multiple_enemies: false` and the entity
  owns only `TargetSpec.AREA` damage skills, no `TargetSpec.SINGLE` ones
- **THEN** the returned `ActionRequest` still uses the owned `AREA` skill against `"all-enemies"` rather
  than returning `None`

#### Scenario: An entity owning no eligible damage skill of either shape returns None
- **WHEN** in legacy mode, the acting `Monster` owns no `ACTIVE` skill whose `effects` include a `damage:`-prefixed ID
- **THEN** `monster_behaviour_policy()` returns `None`, identically to change 9's own
  `default_attack_policy` behaviour for the same condition

### Requirement: Golden fixed-seed tests demonstrate distinct, reproducible behaviour across MonsterTiers
Legacy mode SHALL retain the following existing contract.
`world/rules/tests/` SHALL contain a fixed-seed golden test constructing an identical battlefield (same
enemy roster and stats) faced by one monster from each of the four `MonsterTier` defaults, asserting
that at least the `low` and `calamity` tier monsters make different target choices on that identical
roster, and that every choice is exactly reproducible under the fixture's seed.

#### Scenario: Low-tier and calamity-tier monsters choose different targets on an identical roster
- **WHEN** in legacy mode, the golden fixture's enemy roster contains one low-current-hp, low-`effective_power()` enemy
  and one high-current-hp, high-`effective_power()` enemy, and both a `low`-tier-default and a
  `calamity`-tier-default `Monster` face that identical roster under the same fixed seed
- **THEN** the `low`-tier monster's `monster_behaviour_policy()` output targets the low-hp enemy and the
  `calamity`-tier monster's output targets the high-power enemy

#### Scenario: The golden fixture's decisions are byte-identical across repeated runs under the same seed
- **WHEN** in legacy mode, the golden fixture is run twice under the identical fixed seed and starting battlefield state
- **THEN** every `ActionRequest` `monster_behaviour_policy()` produces across both runs is identical in
  `skill_key` and `targets`

### Requirement: Authored monster kits use shared policy selection and fallback
Legacy mode SHALL retain the following existing contract.
A legacy monster SHALL use its validated authored behavior binding or existing tier default. First-owned selection SHALL prefer the first eligible affordable damage skill in owned order and fall back to an available ordinary attack when either resource or eligibility fails. Declared flee thresholds SHALL retain inclusive priority. Existing target/displacement/knockout gates and initiative-time revalidation SHALL remain authoritative.

#### Scenario: Selection and exhaustion
- **WHEN** in legacy mode, a synthetic first-owned kit executes with full resources then separately exhausted MP and SP
- **THEN** the preferred action executes first and each exhaustion selects available ordinary attack without utility planning

#### Scenario: Threshold and late changes
- **WHEN** in legacy mode, a monster reaches its declared flee edge or targets/eligibility change before resolution
- **THEN** ordinary flee takes inclusive priority and final resolver gates reject invalid late state without creature-specific logic

