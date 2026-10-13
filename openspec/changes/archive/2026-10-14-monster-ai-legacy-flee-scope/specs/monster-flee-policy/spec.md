## MODIFIED Requirements

### Requirement: Flee tuning follows existing tier defaults and instance overrides

Legacy mode SHALL retain the following existing contract.
The flee policy SHALL use `resolve_behaviour_profile(entity)` without a separate tier or monster-key mapping. A monster with no `behaviour_tree` override SHALL receive the threshold of its `threat_tier` default archetype, while a valid override SHALL receive the overridden archetype's threshold. The resolved threshold SHALL drive the legacy body only: the utility decision SHALL NOT derive a flee decision from it, and only the configured typed-invalid-state fallback MAY still reach the legacy body for a utility-mode monster.

#### Scenario: Tier default controls an unoverridden monster

- **WHEN** in legacy mode, a monster has no `behaviour_tree` override
- **THEN** its flee threshold equals the profile referenced by `tier_default_archetype[monster.threat_tier]`

#### Scenario: Instance override controls the flee decision

- **WHEN** in legacy mode, two otherwise identical monsters share a threat tier but one has a valid `behaviour_tree` override with a different flee threshold
- **THEN** each monster's flee decision uses its own resolved profile threshold

### Requirement: The policy checks current-to-maximum true HP at an inclusive boundary

Legacy mode SHALL retain the following existing contract.
For a living, non-fled monster with at least one living, non-fled enemy, `monster_behaviour_policy()` SHALL choose flee exactly when its resolved `flee_hp_fraction` is not `None`, its stored maximum HP is positive, and `stored_current_hp / stored_maximum_hp` is less than or equal to that fraction. It SHALL read true stored combat HP through the combat accessors and SHALL NOT read `disguised_stats` or advance gauge timers. A monster whose effective decision mode is `utility` SHALL NOT evaluate this predicate from its utility decision; only the configured typed-invalid-state fallback MAY reach it, under that fallback's own existing contract.

#### Scenario: Exact threshold chooses flee

- **WHEN** in legacy mode, a monster's stored current HP divided by stored maximum HP exactly equals its non-null `flee_hp_fraction`
- **THEN** `monster_behaviour_policy()` returns a request whose `skill_key` is `"flee"`

#### Scenario: Above threshold preserves attack behavior

- **WHEN** in legacy mode, the same monster's HP fraction is greater than its configured threshold and it has an affordable damage skill
- **THEN** the policy returns the same attack request that 10b's target and skill policy would select

#### Scenario: A non-positive maximum does not divide or choose flee

- **WHEN** in legacy mode, a malformed test entity reports a maximum HP of zero or less
- **THEN** the flee predicate is false and no division-by-zero exception escapes

#### Scenario: Reading the predicate does not advance regeneration

- **WHEN** in legacy mode, the HP gauge has stored current HP and a pending time-based regeneration timestamp
- **THEN** evaluating the flee predicate leaves the complete HP gauge backing data unchanged

### Requirement: Flee selection has priority over attack selection without consuming decision dice

Legacy mode SHALL retain the following existing contract.
After preserving 10b's non-monster delegation and finding living enemies, the monster policy SHALL evaluate flee before enumerating attack skills, selecting targets, selecting area shape, or rolling a seeded tie-break. A monster meeting its threshold SHALL select flee even when it owns no affordable damage skill. A monster with no living, non-fled enemy SHALL return `None` rather than flee. The utility decision SHALL NOT evaluate flee, so this order SHALL constrain the legacy body only — and the configured typed-invalid-state fallback whenever that fallback executes the legacy body.

#### Scenario: Threshold flee does not require a damage skill

- **WHEN** in legacy mode, a monster meets its flee threshold but owns no damage skill or cannot afford any owned damage skill
- **THEN** the policy still returns a `"flee"` request

#### Scenario: Threshold flee consumes no policy tie-break roll

- **WHEN** in legacy mode, a threshold-triggered decision is made on a battlefield that would otherwise require a tied target or skill selection
- **THEN** `dice.roll_d100()` is not called by `monster_behaviour_policy()`

#### Scenario: No enemy means no flee action

- **WHEN** in legacy mode, every opposing combatant is dead or already in `Battlefield.fled`
- **THEN** the policy returns `None`

#### Scenario: Non-monsters retain 10b delegation

- **WHEN** in legacy mode, `monster_behaviour_policy()` receives an entity without `threat_tier`
- **THEN** it delegates to `combat.default_attack_policy()` without evaluating a flee threshold

## ADDED Requirements

### Requirement: Utility mode never voluntarily flees

A monster whose effective decision mode is `utility` SHALL NOT voluntarily flee at any HP fraction, including at or below its resolved `flee_hp_fraction`. Its utility decision SHALL keep the canonical `FLEE_SKILL_KEY` out of its enumerated candidate set, its score terms and any returned `ActionRequest`, proposing its own scored selection when one exists and its own no-action boundary when none does. The configured typed-invalid-state fallback SHALL keep its existing contract.

#### Scenario: The same authored boundary decides differently by effective mode

- **WHEN** two otherwise identical registered monsters resolve to one archetype whose `flee_hp_fraction` is not `null`, each stands at exactly that inclusive boundary with one living enemy and at least one legal damage candidate, and one resolves to `legacy` while the other resolves to `utility`
- **THEN** the legacy monster returns a request whose `skill_key` is the flee key, while the utility monster returns its own scored request whose `skill_key` is a legal damage candidate and never the flee key

#### Scenario: Below the boundary the utility decision still scores

- **WHEN** the utility monster's stored HP fraction falls below the same authored threshold and a legal scored candidate exists
- **THEN** it still returns a scored utility request rather than the flee request, and replaying the identical state, configuration and selection inputs returns that same request

#### Scenario: An empty utility candidate set stays no action

- **WHEN** a living utility monster at or below the same authored threshold owns no legal scored candidate
- **THEN** the policy returns no action rather than the legacy flee request

#### Scenario: The owned flee key is no enumerated candidate

- **WHEN** a utility monster innately owns the canonical flee key and its utility decision reports its enumeration across the HP range up to its maximum
- **THEN** no enumerated candidate, rejected proposal, exclusion, unusable skill, score term or returned request is the flee key

#### Scenario: The typed-invalid-state fallback keeps the legacy body

- **WHEN** a utility-mode monster at or below the boundary raises the typed utility state error while the configured fallback is the legacy fallback
- **THEN** the returned action is that fallback's legacy decision, including its inclusive flee request, and the reported diagnostic names that fallback