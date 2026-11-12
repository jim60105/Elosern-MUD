# Spec Delta

Archive handoff: after syncing this delta, re-list canonical IDs and annotate every new or changed substantive requirement test. Existing requirement headings are intentionally unchanged; historical titles do not preserve superseded mode or dice behavior.

## MODIFIED Requirements

### Requirement: Behaviour parameters are data-driven, not hardcoded in Python
The AI rulebook SHALL own tier-default archetypes and each profile target_strategy, skill_choice, area preference, flee threshold and mode. Evaluating reflex profiles SHALL own reflex_temperature there. The area-preference field SHALL influence only deliberation scoring. Python SHALL NOT duplicate authored strategy, tier mapping or temperature tuning.

#### Scenario: No archetype or tier-mapping literal is hardcoded in Python
- **WHEN** a synthetic valid rulebook changes tier mapping, strategy or reflex temperature
- **THEN** resolved decisions use those authored values without a separate balance authority

#### Scenario: Every archetype declares all three tunable parameters
- **WHEN** a profile declares target strategy, skill strategy and area preference
- **THEN** recognized strategies and boolean area preference remain validated; no reflex shape gate reads the flag

#### Scenario: The tier default mapping covers every MonsterTier registry key
- **WHEN** a synthetic tier registry and rulebook are loaded
- **THEN** each registered tier has exactly one default referencing an existing profile; missing or unknown references fail validation

### Requirement: Monster.behaviour_tree resolves to a real archetype, defaulting from threat_tier
`world/rules/monster_behaviour.py` SHALL provide `resolve_behaviour_profile(monster) ->
BehaviourProfile`, reading `monster.behaviour_tree` as an optional override key into
`MONSTER_BEHAVIOUR_YAML["archetypes"]` and falling back to `MONSTER_BEHAVIOUR_YAML
["tier_default_archetype"][monster.threat_tier]` when `behaviour_tree` is unset (its change-3-declared
placeholder value). Deliberation mode and intelligence resolution SHALL respect this actual stored binding.

#### Scenario: An unset behaviour_tree resolves to the tier's default archetype
- **WHEN** `resolve_behaviour_profile(monster)` is called for a `Monster` whose `behaviour_tree` holds
  its change-3 placeholder (unset) value and whose `threat_tier` is `"mid"`
- **THEN** the returned `BehaviourProfile` matches `MONSTER_BEHAVIOUR_YAML["archetypes"]
  [MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]["mid"]]` exactly

#### Scenario: A set behaviour_tree overrides the tier default
- **WHEN** `resolve_behaviour_profile(monster)` is called for a `Monster` whose `threat_tier` is
  `"high"` and whose `behaviour_tree` is set to an archetype key that is not `"high"`'s tier default
- **THEN** the returned `BehaviourProfile` matches the overriding archetype, not `"high"`'s default

#### Scenario: This change requires no edit to typeclasses/monsters.py
- **WHEN** behavior and deliberation tuning are resolved for a constructed registered monster
- **THEN** its species, variant, behavior binding, stats and persistent attributes remain unchanged; no intelligence trait is copied to the entity

### Requirement: Variant intelligence is explicit and independent
The system SHALL accept intelligence only as an explicit registered-variant integer from 0 through 100. Every effective deliberation variant SHALL have a validated value. Intelligence SHALL change decision evaluation only and SHALL NOT change stats, resources, owned skills, proficiency or combat formulas.

#### Scenario: Independent variants
- **WHEN** two variants of the same species have independently authored intelligence, including a stronger variant with lower intelligence
- **THEN** both values resolve unchanged; tiers, species and archetypes provide no intelligence value

#### Scenario: Invalid authored values
- **WHEN** intelligence is missing for effective deliberation, boolean, fractional, out of range, or attached to an unregistered variant or invalid species relationship
- **THEN** startup rejects the tuning; supplied reflex intelligence values are validated too

### Requirement: Mode selection honors actual variant and behavior binding
Effective mode SHALL accept only reflex or deliberation, using a validated variant override or the actual resolved archetype mode. Missing archetype mode SHALL mean reflex. Deliberation without a valid runtime species/variant pair or explicit intelligence SHALL produce a typed invalid state. Former mode values SHALL be rejected without aliases or migration.

#### Scenario: Runtime repair changes binding
- **WHEN** a registered variant override differs from its actual resolved archetype mode
- **THEN** the validated override wins; absent override uses the actual stored behavior binding and validates the species/variant pair

#### Scenario: Legacy remains available
- **WHEN** an untuned reflex variant, tier-only monster or unregistered monster decides
- **THEN** reflex remains usable without invented intelligence

#### Scenario: Former names rejected
- **WHEN** a profile or variant mode map supplies legacy or utility
- **THEN** startup raises its named configuration error; neither is an alias

### Requirement: AI tuning is strict and startup scoped
Startup SHALL validate mandatory behavior fields, optional mode, complete named utility weights, variant maps and budget. highest_expected_damage profiles SHALL author finite positive non-boolean reflex_temperature; first_owned MAY omit it but supplied values SHALL validate. Unknown fields/modes, invalid primitive types, negative/non-finite weights and non-integer budgets outside 1..4096 SHALL be rejected.

#### Scenario: Strict temperature
- **WHEN** a highest_expected_damage profile omits reflex_temperature or supplies zero, negative, boolean, nonnumeric or non-finite temperature
- **THEN** startup rejects it, even when its current effective mode is deliberation

#### Scenario: First owned needs no temperature
- **WHEN** first_owned omits temperature or supplies a valid one
- **THEN** both load and produce the same deterministic first authored skill; invalid supplied temperature is rejected

#### Scenario: Strict profiles
- **WHEN** a synthetic profile omits a mandatory behavior field or has malformed weights, mode or budget
- **THEN** the existing named configuration error remains authoritative

#### Scenario: All archetypes remain distinct
- **WHEN** a synthetic rulebook declares distinct valid profiles with different preferences
- **THEN** loading retains each profile's authored preferences without collapsing them or fixing a shipped profile roster

#### Scenario: Independent temperatures
- **WHEN** a deliberation profile has a valid reflex_temperature and explicit variant intelligence
- **THEN** deliberation uses its intelligence-based temperature and does not read reflex_temperature for scoring or sampling

### Requirement: Session tuning has a reproducible lifetime
The system SHALL record immutable resolved session tuning and its fingerprint in process. Fingerprints SHALL include algorithm version, modes, reflex temperatures and primary-damage descriptors alongside existing tuning inputs. Startup configuration SHALL remain fixed without hot reload. Restart SHALL clear recorded tuning and reconstruct sessions from validated startup configuration without durable AI fields.

#### Scenario: Active session and restart
- **WHEN** configuration changes on disk while a session is active, then the process restarts
- **THEN** the running process retains recorded tuning; reconstructed sessions use startup tuning and empty history

#### Scenario: Fingerprint inputs
- **WHEN** algorithm version, mode spelling, reflex temperature or primary damage coefficient changes independently
- **THEN** each change alters the fingerprint; display names and object addresses do not

#### Scenario: Stable equivalent input
- **WHEN** identical tuning and primary damage metadata are loaded with different mapping insertion order
- **THEN** the same canonical fingerprint is produced

### Requirement: Owned support actives bind an effective utility decision
The shipped startup tuning SHALL resolve an effective deliberation decision mode for every registered variant that owns an active skill without a damage effect, judged by the same damage predicate the reflex decision body applies. The check SHALL report each violating variant and skill, SHALL carry no variant roster, and SHALL NOT prevent an edited reflex rollback tuning from loading.

#### Scenario: Legacy support kit reported
- **WHEN** a synthetic variant owning a self-only support skill without damage resolves a reflex decision mode under a synthetic tuning
- **THEN** the check reports that variant and skill

#### Scenario: Utility support kit accepted
- **WHEN** the same variant receives a validated deliberation override with explicit intelligence, or binds an archetype whose mode is deliberation
- **THEN** the check reports nothing for it

#### Scenario: Damage kits keep any mode
- **WHEN** a synthetic variant owns only actives with a damage effect under a reflex decision mode
- **THEN** the check reports nothing for it

#### Scenario: Shipped tuning and rollback
- **WHEN** the check runs over the shipped registries and startup tuning, and the shipped rulebook is reloaded with every mode override removed
- **THEN** the shipped tuning reports nothing, and the rollback tuning loads without error
