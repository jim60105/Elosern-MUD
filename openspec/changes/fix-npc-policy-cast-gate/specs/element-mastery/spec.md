## ADDED Requirements

### Requirement: can_cast_skill is the shared side-effect-free cast-eligibility predicate

`world/rules/progression.py` SHALL define `can_cast_skill(entity, skill) -> bool`, a pure, side-effect-free query returning `True` when the given skill is not an elemental spell (`spell_tier_for(skill)` returns `None`), and otherwise delegating to `can_cast_spell_tier(entity, skill.element.key, tier)` for the skill's derived tier. A `ValueError` raised by either underlying query (malformed MP cost outside every tier band, an unrecognized element key, or an unknown tier) SHALL be converted to `False` — the predicate fails closed and never propagates. `ActionResolver`'s ownership step and every deterministic AI combat policy SHALL consume this single predicate for spell-tier eligibility; the predicate SHALL NOT read `magic_rank_title`, consult `conferred_grants()`, or write any entity state.

#### Scenario: A non-elemental skill always passes the gate

- **WHEN** `can_cast_skill(entity, basic_attack)` is called on any entity that owns `basic_attack` (an ACTIVE skill with no MP cost and therefore no tier)
- **THEN** it returns `True` regardless of the entity's magic level

#### Scenario: An over-tier elemental spell fails closed

- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with `magic_level.value == 15`, no declared affinities, and no owned `fire_mastery` (firestorm's 30 MP cost derives the 術師 tier, and `floor(15 * 1.0) == 15` is below the 16 threshold)
- **THEN** it returns `False`, exactly as `ActionResolver` would reject the cast

#### Scenario: The mastery override unlocks a spell through the predicate

- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with `magic_level.value == 1` whose `owned_keys()` contains `"fire_mastery"`
- **THEN** it returns `True`

#### Scenario: A favored affinity boundary passes through the predicate

- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with `magic_level.value == 15` and `entity.db.affinity_elements == ["fire"]`
- **THEN** it returns `True`, because `floor(15 * 1.1) == 16` meets the 術師 threshold

#### Scenario: A malformed elemental spell is denied, not raised

- **WHEN** `can_cast_skill(entity, skill)` is called for an elemental spell whose MP cost is missing, non-positive, or outside every tier band (so `spell_tier_for` raises `ValueError`), or whose element is unrecognized
- **THEN** it returns `False` instead of raising, so policy and preview consumers never see an exception from a content-authoring error
