## MODIFIED Requirements

### Requirement: Behaviour parameters are data-driven, not hardcoded in Python
The existing AI rulebook SHALL declare a `tier_default_archetype` mapping (one
archetype key per `MonsterTier` registry key) and an `archetypes` table, where every entry declares
`target_strategy`, `skill_choice`, and `prefer_area_when_multiple_enemies`. No balance-relevant value
(which strategy an archetype uses, which archetype a tier defaults to) SHALL appear as a Python literal
anywhere in `world/rules/monster_behaviour.py`.

#### Scenario: The tier default mapping covers every MonsterTier registry key
- **WHEN** `MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]` is inspected
- **THEN** it contains exactly one entry for every key present in `world.lore.monsters.MONSTER_TIER_REGISTRY`
  (`low`, `mid`, `high`, `calamity`), and every mapped value exists as a key in
  `MONSTER_BEHAVIOUR_YAML["archetypes"]`

#### Scenario: Every archetype declares all three tunable parameters
- **WHEN** every entry in `MONSTER_BEHAVIOUR_YAML["archetypes"]` is inspected
- **THEN** each has a `target_strategy` value of `"lowest_hp"` or `"highest_effective_power"`, a
  `skill_choice` value of `"first_owned"` or `"highest_expected_damage"`, and a boolean
  `prefer_area_when_multiple_enemies`

#### Scenario: No archetype or tier-mapping literal is hardcoded in Python
- **WHEN** a synthetic rulebook changes a strategy or tier default and startup validation succeeds
- **THEN** resolved profiles and actual legacy decisions use those authored values without a separate balance authority

### Requirement: Monster.behaviour_tree resolves to a real archetype, defaulting from threat_tier
`world/rules/monster_behaviour.py` SHALL provide `resolve_behaviour_profile(monster) ->
BehaviourProfile`, reading `monster.behaviour_tree` as an optional override key into
`MONSTER_BEHAVIOUR_YAML["archetypes"]` and falling back to `MONSTER_BEHAVIOUR_YAML
["tier_default_archetype"][monster.threat_tier]` when `behaviour_tree` is unset (its change-3-declared
placeholder value). Utility mode and intelligence resolution SHALL respect this actual stored binding.

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
- **WHEN** behavior and utility tuning are resolved for a constructed registered monster
- **THEN** its species, variant, behavior binding, stats and persistent attributes remain unchanged; no intelligence trait is copied to the entity

## ADDED Requirements

### Requirement: Variant intelligence is explicit and independent
The system SHALL accept intelligence only as an explicit registered-variant integer from 0 through 100. Every effective utility variant SHALL have a validated value. Intelligence SHALL change decision evaluation only and SHALL NOT change stats, resources, owned skills, proficiency or combat formulas.

#### Scenario: Independent variants
- **WHEN** two variants of the same species have independently authored intelligence, including a stronger variant with lower intelligence
- **THEN** both values resolve unchanged; tiers, species and archetypes provide no intelligence value

#### Scenario: Invalid authored values
- **WHEN** intelligence is missing for effective utility, boolean, fractional, out of range, or attached to an unregistered variant or invalid species relationship
- **THEN** startup rejects the tuning; supplied legacy intelligence values are validated too

### Requirement: Mode selection honors actual variant and behavior binding
The effective mode SHALL use a validated variant override when present and otherwise the actual resolved archetype mode. Missing archetype mode SHALL mean legacy. Utility without a valid runtime species/variant pair or explicit intelligence SHALL produce a typed invalid decision state.

#### Scenario: Runtime repair changes binding
- **WHEN** stored behavior binding or species/variant relationship differs from its original construction
- **THEN** resolution uses the actual binding, validates the pair and never trusts a variant string alone

#### Scenario: Legacy remains available
- **WHEN** an untuned legacy variant, tier-only monster or unregistered monster decides
- **THEN** legacy remains available without invented utility intelligence

### Requirement: AI tuning is strict and startup scoped
Startup SHALL validate four mandatory legacy fields, optional decision_mode and complete named utility weights, variant maps and candidate budget. Unknown fields, invalid modes, primitive types, boolean numbers, negative or non-finite weights and budgets outside integer 1..4096 SHALL be rejected.

#### Scenario: Strict profiles
- **WHEN** a synthetic profile has one malformed field or omits a mandatory legacy field
- **THEN** loading fails with a named configuration error instead of accepting partial tuning

#### Scenario: All archetypes remain distinct
- **WHEN** the validated six archetypes are loaded
- **THEN** instinctive, pack_hunter, brute, tactical_caster, apex_predator and ambush_predator remain available with their authored preferences

### Requirement: Session tuning has a reproducible lifetime
The system SHALL record immutable resolved tuning and its fingerprint in process for a session. Startup configuration SHALL remain fixed without hot reload. Restart SHALL clear recorded tuning and reconstruct existing sessions with validated startup configuration; no durable AI fields or per-entity intelligence copies SHALL be added.

#### Scenario: Active session and restart
- **WHEN** configuration changes on disk while a session is active, then the server restarts
- **THEN** the active process retains its recorded tuning; reconstructed sessions use startup tuning and empty history

#### Scenario: Fingerprint inputs
- **WHEN** algorithm, intelligence, mode, weight, budget or relevant estimation rule changes
- **THEN** the fingerprint changes without using display names or object addresses

