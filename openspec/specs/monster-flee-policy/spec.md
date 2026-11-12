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

Reflex flee SHALL use the actual resolved behavior profile, taking its tier default when no override exists and its valid instance override otherwise. No separate tier or monster-key flee mapping SHALL exist. Deliberation SHALL NOT derive voluntary flee from this tuning. Only configured typed-invalid-state reflex fallback MAY reach the reflex flee body for a deliberation-mode monster.

#### Scenario: Tier default controls an unoverridden monster
- **WHEN** a reflex monster has no behavior override
- **THEN** its flee threshold equals its authored tier-default profile threshold

#### Scenario: Instance override controls the flee decision
- **WHEN** two otherwise identical reflex monsters share a tier but one has a valid behavior override with a different threshold
- **THEN** each uses its own resolved threshold

### Requirement: The policy checks current-to-maximum true HP at an inclusive boundary

For a living non-fled monster with a living non-fled enemy, reflex SHALL choose flee exactly when its resolved threshold is non-null, stored maximum HP is positive and stored current HP divided by stored maximum HP is at most the threshold. It SHALL read true stored HP without regeneration or disguised stats. Deliberation SHALL NOT evaluate this predicate except through configured typed-invalid-state reflex fallback.

#### Scenario: Exact threshold chooses flee
- **WHEN** a reflex monster is at its non-null inclusive threshold
- **THEN** the policy returns the canonical flee skill request

#### Scenario: Above threshold preserves attack behavior
- **WHEN** a reflex monster is above its threshold and has a usable damage skill
- **THEN** the current reflex skill strategy selects the attack without changing the threshold contract

#### Scenario: A non-positive maximum does not divide or choose flee
- **WHEN** stored maximum HP is non-positive
- **THEN** the flee predicate is false without division or a flee request

#### Scenario: Reading the predicate does not advance regeneration
- **WHEN** a valid gauge has a pending regeneration timestamp
- **THEN** reading the flee predicate leaves its complete backing data and timestamp unchanged

### Requirement: Flee selection has priority over attack selection without consuming decision dice

After non-monster delegation and finding living enemies, reflex SHALL evaluate flee before enumerating attack skills, choosing targets or shapes, or sampling a skill. Meeting the threshold SHALL choose flee even without affordable damage skills. A flee decision SHALL consume neither combat dice nor independent skill-selection RNG. With no living non-fled enemy it SHALL return None. Deliberation SHALL NOT evaluate voluntary flee.

#### Scenario: Threshold flee does not require a damage skill
- **WHEN** a reflex monster meets its threshold with either no usable damage kit or multiple kits requiring stochastic skill selection
- **THEN** it returns flee without calling either combat dice or the independent selection RNG

#### Scenario: Threshold flee consumes no policy tie-break roll
- **WHEN** a threshold-triggered reflex decision would otherwise require tied target or stochastic skill selection
- **THEN** flee returns before any target tie roll or independent skill-selection draw

#### Scenario: No enemy means no flee action
- **WHEN** every opponent is dead or fled
- **THEN** the policy returns None

#### Scenario: Non-monsters retain 10b delegation
- **WHEN** the entity has no monster threat tier
- **THEN** it delegates to the existing default attack policy without evaluating flee

### Requirement: A flee decision is a complete ActionResolver request and never a state mutation

A threshold-triggered decision SHALL import and use 10c's canonical `FLEE_SKILL_KEY` from `world.rules.disengage`, thereby loading 10c's skill and effect-handler registrations, and return one self-targeted `ActionRequest` with actor equal to the monster, targets equal to `[monster]`, and a `BattlefieldActionContext` for the same battlefield whose `event_context["battlefield"]` references that battlefield. The policy SHALL NOT call `ActionResolver.resolve()` nor roll flee success.

#### Scenario: Request carries the disengage handler context

- **WHEN** the flee predicate is true
- **THEN** the returned request has the exact actor, self target, `FLEE_SKILL_KEY`, targeting battlefield, and event-context battlefield required by 10c

#### Scenario: Importing monster behaviour is sufficient to load flee registration

- **WHEN** a fresh interpreter imports `world.rules.monster_behaviour` without first importing `world.rules.disengage` elsewhere
- **THEN** `FLEE_SKILL_KEY` exists in `SKILL_REGISTRY`, its effect handler is registered, and a threshold-generated request does not reject as `UNKNOWN_SKILL`

#### Scenario: Decision alone changes no state

- **WHEN** a complete snapshot is taken before calling the policy for a threshold-triggered monster
- **THEN** the returned request is a pure proposal and the battlefield and every entity snapshot remain unchanged

#### Scenario: The policy mutates no listed state surface
- **WHEN** the flee policy runs for a threshold-triggered monster
- **THEN** it leaves `Battlefield.fled`, traits, sexual state, buffs, skill grants, inventory, and currency unchanged

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

The flee predicate SHALL use no LLM, network or random draw. Archetype thresholds SHALL remain rulebook-authored. Fixed profile and stored HP state SHALL reproduce the flee-versus-attack decision; fixed resolver dice SHALL reproduce a chosen flee's resolution. Attack skill sampling after a false flee predicate SHALL follow the current reflex contract and SHALL NOT redefine the deterministic flee boundary.

#### Scenario: Fixed state reproduces the same decision
- **WHEN** equivalent battlefields use identical profiles and stored HP with different injected skill-selection RNG states
- **THEN** both make the same flee-versus-attack decision; a chosen flee consumes no selection draw

#### Scenario: Deterministic core has no generative dependency
- **WHEN** external model and network access are unavailable and the flee predicate is evaluated
- **THEN** its decision succeeds without persistent state changes and reads the authored threshold

### Requirement: Utility mode never voluntarily flees

A deliberation monster SHALL NOT voluntarily flee at any HP fraction. Its deliberation candidates, scores and returned requests SHALL exclude the canonical flee skill, selecting its scored action when available and returning None when no scored action exists. Configured typed-invalid-state reflex fallback SHALL retain its inclusive flee contract and diagnostic identity.

#### Scenario: The same authored boundary decides differently by effective mode
- **WHEN** otherwise identical synthetic registered monsters meet a non-null threshold with a living enemy and legal damage action, one in reflex and one in deliberation
- **THEN** reflex returns flee and deliberation returns its scored damage action, never flee

#### Scenario: Below the boundary the utility decision still scores
- **WHEN** deliberation is below its profile threshold with a legal scored candidate
- **THEN** it returns its scored request; identical state, configuration and selection inputs replay that request

#### Scenario: An empty utility candidate set stays no action
- **WHEN** a living deliberation monster at or below the threshold has no legal scored candidate
- **THEN** it returns None without reflex flee fallback

#### Scenario: The owned flee key is no enumerated candidate
- **WHEN** deliberation owns innate flee and reports its enumeration at different HP fractions
- **THEN** no candidate, rejected proposal, exclusion, unusable skill, score term or returned request names flee

#### Scenario: The typed-invalid-state fallback keeps the legacy body
- **WHEN** deliberation raises its typed invalid-state error at or below the threshold with configured reflex fallback
- **THEN** the fallback returns its inclusive reflex flee request and the diagnostic identifies reflex
