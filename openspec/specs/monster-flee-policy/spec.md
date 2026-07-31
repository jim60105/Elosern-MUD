# Monster Flee Policy Specification

## Purpose

Define deterministic, YAML-tuned monster flee decisions that produce canonical
disengage action requests while leaving combat state mutation to the action
resolver.

## Requirements

### Requirement: Every monster behaviour archetype declares a validated flee threshold

Each entry in `world/rules/rulebook/monster_behaviour.yaml`'s `archetypes` mapping SHALL declare `flee_hp_fraction` as either YAML `null` or a real number in the inclusive range `[0.0, 1.0]`. `BehaviourProfile` SHALL expose the same field. `null` SHALL mean that the archetype never voluntarily chooses flee.

#### Scenario: All shipped archetypes declare valid thresholds

- **WHEN** the shipped monster behaviour rulebook is loaded
- **THEN** every archetype produces a frozen `BehaviourProfile` whose `flee_hp_fraction` is `None` or a number between `0.0` and `1.0` inclusive

#### Scenario: Null disables voluntary flee

- **WHEN** a monster resolves to an archetype whose `flee_hp_fraction` is `null`, at any positive HP
- **THEN** the flee branch is not selected

#### Scenario: Invalid threshold data fails loudly

- **WHEN** a profile supplies a boolean, string, number below `0.0`, or number above `1.0` as `flee_hp_fraction`, or omits the field
- **THEN** rulebook validation raises `MonsterBehaviourConfigError` with message prefix `invalid monster behaviour rulebook:` before profiles are constructed

### Requirement: Flee tuning follows existing tier defaults and instance overrides

The flee policy SHALL use `resolve_behaviour_profile(entity)` without a separate tier or monster-key mapping. A monster with no `behaviour_tree` override SHALL receive the threshold of its `threat_tier` default archetype, while a valid override SHALL receive the overridden archetype's threshold.

#### Scenario: Tier default controls an unoverridden monster

- **WHEN** a monster has no `behaviour_tree` override
- **THEN** its flee threshold equals the profile referenced by `tier_default_archetype[monster.threat_tier]`

#### Scenario: Instance override controls the flee decision

- **WHEN** two otherwise identical monsters share a threat tier but one has a valid `behaviour_tree` override with a different flee threshold
- **THEN** each monster's flee decision uses its own resolved profile threshold

### Requirement: The policy checks current-to-maximum true HP at an inclusive boundary

For a living, non-fled monster with at least one living, non-fled enemy, `monster_behaviour_policy()` SHALL choose flee exactly when its resolved `flee_hp_fraction` is not `None`, its stored maximum HP is positive, and `stored_current_hp / stored_maximum_hp` is less than or equal to that fraction. It SHALL read true stored combat HP through the combat accessors and SHALL NOT read `disguised_stats` or advance gauge timers.

#### Scenario: Exact threshold chooses flee

- **WHEN** a monster's stored current HP divided by stored maximum HP exactly equals its non-null `flee_hp_fraction`
- **THEN** `monster_behaviour_policy()` returns a request whose `skill_key` is `"flee"`

#### Scenario: Above threshold preserves attack behavior

- **WHEN** the same monster's HP fraction is greater than its configured threshold and it has an affordable damage skill
- **THEN** the policy returns the same attack request that 10b's target and skill policy would select

#### Scenario: A non-positive maximum does not divide or choose flee

- **WHEN** a malformed test entity reports a maximum HP of zero or less
- **THEN** the flee predicate is false and no division-by-zero exception escapes

#### Scenario: Reading the predicate does not advance regeneration

- **WHEN** the HP gauge has stored current HP and a pending time-based regeneration timestamp
- **THEN** evaluating the flee predicate leaves the complete HP gauge backing data unchanged

### Requirement: Flee selection has priority over attack selection without consuming decision dice

After preserving 10b's non-monster delegation and finding living enemies, the monster policy SHALL evaluate flee before enumerating attack skills, selecting targets, selecting area shape, or rolling a seeded tie-break. A monster meeting its threshold SHALL select flee even when it owns no affordable damage skill. A monster with no living, non-fled enemy SHALL return `None` rather than flee.

#### Scenario: Threshold flee does not require a damage skill

- **WHEN** a monster meets its flee threshold but owns no damage skill or cannot afford any owned damage skill
- **THEN** the policy still returns a `"flee"` request

#### Scenario: Threshold flee consumes no policy tie-break roll

- **WHEN** a threshold-triggered decision is made on a battlefield that would otherwise require a tied target or skill selection
- **THEN** `dice.roll_d100()` is not called by `monster_behaviour_policy()`

#### Scenario: No enemy means no flee action

- **WHEN** every opposing combatant is dead or already in `Battlefield.fled`
- **THEN** the policy returns `None`

#### Scenario: Non-monsters retain 10b delegation

- **WHEN** `monster_behaviour_policy()` receives an entity without `threat_tier`
- **THEN** it delegates to `combat.default_attack_policy()` without evaluating a flee threshold

### Requirement: A flee decision is a complete ActionResolver request and never a state mutation

A threshold-triggered decision SHALL import and use 10c's canonical `FLEE_SKILL_KEY` from `world.rules.disengage`, thereby loading 10c's skill and effect-handler registrations, and return one self-targeted `ActionRequest` with actor equal to the monster, targets equal to `[monster]`, and a `BattlefieldActionContext` for the same battlefield whose `event_context["battlefield"]` references that battlefield. The policy SHALL NOT call `ActionResolver.resolve()`, roll flee success, or mutate `Battlefield.fled`, traits, sexual state, buffs, skill grants, inventory, or currency.

#### Scenario: Request carries the disengage handler context

- **WHEN** the flee predicate is true
- **THEN** the returned request has the exact actor, self target, `FLEE_SKILL_KEY`, targeting battlefield, and event-context battlefield required by 10c

#### Scenario: Importing monster behaviour is sufficient to load flee registration

- **WHEN** a fresh interpreter imports `world.rules.monster_behaviour` without first importing `world.rules.disengage` elsewhere
- **THEN** `FLEE_SKILL_KEY` exists in `SKILL_REGISTRY`, its effect handler is registered, and a threshold-generated request does not reject as `UNKNOWN_SKILL`

#### Scenario: Decision alone changes no state

- **WHEN** a complete snapshot is taken before calling the policy for a threshold-triggered monster
- **THEN** the returned request is a pure proposal and the battlefield and every entity snapshot remain unchanged

### Requirement: Existing combat orchestration resolves monster flee through the sole writer

When the request returned by the policy is used as the action provider output for `run_round()` or `resolve_overwhelm()`, those existing orchestrators SHALL pass it through `ActionResolver.resolve()`. A successful 10c disengage SHALL add the monster key to `Battlefield.fled`; a failed disengage SHALL leave the key absent, and either attempt SHALL consume that monster's turn without an attack.

#### Scenario: Successful monster flee leaves combat

- **WHEN** the policy selects flee and 10c's fixed flee roll succeeds during `run_round()`
- **THEN** the monster key is added to `Battlefield.fled`, it deals no attack damage that turn, and existing combat logic excludes it from later turns, targeting, and team-power aggregation

#### Scenario: Failed monster flee costs the turn

- **WHEN** the policy selects flee and 10c's fixed flee roll fails during `run_round()`
- **THEN** the monster remains outside `Battlefield.fled`, deals no attack damage that turn, and the attempt produces 10c's normal EventLog

#### Scenario: Overwhelm uses the same policy request

- **WHEN** `resolve_overwhelm()` invokes `monster_behaviour_policy()` for a threshold-triggered monster
- **THEN** the request resolves without a special branch in `overwhelm.py`, and successful flight is reflected in the next existing overwhelm reclassification

### Requirement: Monster flee decisions remain deterministic, offline, and YAML-tuned

The flee policy SHALL make no LLM, network, or Python-random call. All archetype threshold values SHALL reside in `monster_behaviour.yaml`, and fixed entity state plus fixed resolver dice SHALL produce the same request and resolution outcome across repeated runs.

#### Scenario: Fixed state reproduces the same decision

- **WHEN** two equivalent battlefields use identical monster profiles, HP state, and fixed resolver dice
- **THEN** both runs produce identical flee-versus-attack decisions and identical resolution outcomes

#### Scenario: Deterministic core has no generative dependency

- **WHEN** the changed monster behaviour source is inspected
- **THEN** it imports no `world.ai` module, performs no network call, and contains no balance threshold literal for a shipped archetype
