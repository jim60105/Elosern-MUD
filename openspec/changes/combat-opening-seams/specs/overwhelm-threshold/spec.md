## ADDED Requirements

### Requirement: A pure query answers whether a commanded action damages an enemy, read statically from the skill definition
`world/rules/overwhelm.py` SHALL provide
`commanded_damage_reaches_enemy(battlefield, actor_key, skill_key, target_keys) -> bool`, returning
`True` only when both conditions hold: the skill definition resolved from `SKILL_REGISTRY` for
`skill_key` carries at least one `world.skills.effects.DamageEffect` among its parsed `effects`,
**and** at least one member of `target_keys` belongs to the `battlefield` team opposing
`battlefield.team_of(actor_key)`. `target_keys` SHALL be an iterable of concrete roster keys;
resolving an approved AREA shorthand into concrete keys is the caller's responsibility, and a value
that is not a concrete roster key SHALL simply fail to match the enemy team rather than raise.
A `skill_key` absent from `SKILL_REGISTRY` SHALL return `False` without raising.

#### Scenario: A damage skill aimed at an enemy is the only true case
- **WHEN** `commanded_damage_reaches_enemy()` is called for a skill whose effects include
  `damage:<element>:<school>` and a `target_keys` containing one member of the opposing team
- **THEN** it returns `True`

#### Scenario: A non-damaging skill is false however it is aimed
- **WHEN** the query is called for a pure buff, a heal, a self-heal, a cleanse, a debuff-only
  application, a disguise, or a movement skill, with `target_keys` naming enemies
- **THEN** it returns `False`

#### Scenario: A composite skill carrying damage alongside other effects is true
- **WHEN** the query is called for a skill whose effects include both `damage:<element>:<school>`
  and a `buff_apply:<key>` entry, aimed at an enemy
- **THEN** it returns `True`

#### Scenario: A damage skill aimed only at allies or the actor is false
- **WHEN** the query is called for a damaging skill whose `target_keys` contain only the actor's own
  key, only allied team members, or nothing at all
- **THEN** it returns `False`

#### Scenario: Indirect hp movement is deliberately excluded
- **WHEN** the query is called for a skill whose effects include a `SexualDrainEffect` (which moves
  a target's pleasure into the caster's own hp, mp, and sp) but no `DamageEffect`, aimed at an enemy
- **THEN** it returns `False`, because the query reads `DamageEffect` alone

#### Scenario: An unknown skill key is false, not an error
- **WHEN** the query is called with a `skill_key` that `SKILL_REGISTRY` does not contain
- **THEN** it returns `False` and raises nothing

### Requirement: The damage query is side-effect free, roll-free, and recomputable
`commanded_damage_reaches_enemy()` SHALL NOT call `roll_d100()`, construct a `PendingEffect`, write
to any entity attribute, cache a previous result, or require being called in any particular sequence
relative to `classify_overwhelm()` or any other function — the same purity discipline
`classify_overwhelm()` already carries. It SHALL NOT be called from inside `classify_overwhelm()`:
the two answer independent questions, and combining them is the dispatching caller's decision.

#### Scenario: The implementation performs no roll and no write
- **WHEN** `commanded_damage_reaches_enemy()`'s implementation is inspected
- **THEN** it contains no call to `roll_d100()`, no `PendingEffect` construction, and no assignment
  to any entity's `traits`, `buffs`, or `sexual` state — it is computed from a registry lookup and
  `battlefield` team membership alone

#### Scenario: Repeated calls on unchanged state agree
- **WHEN** the query is called twice with identical arguments against an unmutated `battlefield`
- **THEN** both calls return the same value, and no state observable to `classify_overwhelm()` has
  changed between them

#### Scenario: classify_overwhelm does not consult the damage query
- **WHEN** `classify_overwhelm()`'s implementation is inspected after this change
- **THEN** it does not call `commanded_damage_reaches_enemy()`, and its verdict for a given
  `battlefield` is unchanged by this change
