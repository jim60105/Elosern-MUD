## ADDED Requirements

### Requirement: Behaviour parameters are data-driven, not hardcoded in Python
`world/rules/rulebook/monster_behaviour.yaml` SHALL declare a `tier_default_archetype` mapping (one
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
- **WHEN** `world/rules/monster_behaviour.py`'s source is inspected
- **THEN** it contains no string literal matching an archetype key or a `MonsterTier` key outside of
  test fixtures — every such value is read from `MONSTER_BEHAVIOUR_YAML`, loaded from
  `rulebook/monster_behaviour.yaml`

### Requirement: Behaviour tiers are grounded in MonsterTier and named world_info.md examples, not
invented flavour
The tier→archetype defaults SHALL correspond to distinct decision-making behaviour for at least the four
`MonsterTier` bands, and at least one archetype SHALL exist that is not any tier's own default, reserved
for a named example within a tier whose `world_info.md` description differs qualitatively from that
tier's other examples.

#### Scenario: Low, mid, high, and calamity tiers each default to a distinct archetype
- **WHEN** `MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]` is inspected for all four `MonsterTier`
  keys
- **THEN** no two tiers map to the same archetype key

#### Scenario: An archetype exists for a named example that diverges from its tier's default
- **WHEN** `MONSTER_BEHAVIOUR_YAML["archetypes"]` is inspected
- **THEN** it contains at least one archetype key that is not the default for any `MonsterTier`,
  intended for a specific `world_info.md`-named monster (e.g. 魔法生物 within the `high` tier, whose
  tier default is a different archetype) whose documented nature differs from that tier's modal example

#### Scenario: Low-tier and mid-tier archetypes share a target strategy but differ on skill sophistication
- **WHEN** the `low` and `mid` tier default archetypes' `target_strategy` and `skill_choice` values are
  compared
- **THEN** both use `target_strategy: lowest_hp`, but their `skill_choice` values differ — reflecting
  `world_info.md`'s framing of low-tier monsters (史萊姆/哥布林/巨鼠) as unsophisticated opportunists and
  mid-tier monsters (狼型魔獸/食人魔/地龍) as coordinated pack hunters that still target the weakest prey

#### Scenario: High-tier and calamity-tier archetypes target the greatest threat, not the weakest
- **WHEN** the `high` and `calamity` tier default archetypes' `target_strategy` values are inspected
- **THEN** both are `highest_effective_power`, reflecting `world_info.md`'s framing of these tiers as at
  or beyond the human combat ceiling, with no reason to avoid the strongest available target

### Requirement: Monster.behaviour_tree resolves to a real archetype, defaulting from threat_tier
`world/rules/monster_behaviour.py` SHALL provide `resolve_behaviour_profile(monster) ->
BehaviourProfile`, reading `monster.behaviour_tree` as an optional override key into
`MONSTER_BEHAVIOUR_YAML["archetypes"]` and falling back to `MONSTER_BEHAVIOUR_YAML
["tier_default_archetype"][monster.threat_tier]` when `behaviour_tree` is unset (its change-3-declared
placeholder value). This is the first code to give `Monster.behaviour_tree` consumed meaning.

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
- **WHEN** `typeclasses/monsters.py` is compared before and after this change lands
- **THEN** the file is byte-identical — `Monster.behaviour_tree` and `Monster.threat_tier` already exist
  as change 3 built them; this change only reads them
