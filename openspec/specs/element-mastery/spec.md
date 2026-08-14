## Purpose

Element mastery ties the display rank title and the mechanical cast gate to an
entity's numeric magic level, with direct ownership of an element's mastery
skill overriding the gate. Everything here is a pure, side-effect-free query;
nothing in this capability writes game state.

## Requirements

### Requirement: magic_rank_title derives a display-only title from numeric magic level
`world/rules/progression.py` SHALL define `magic_rank_title(entity) -> str`, a pure function returning
one of `"學徒"`, `"術師"`, `"大師"`, `"賢者"`, `"主宰"` based on `entity.traits.magic_level.value`
against the bands 0–15 / 16–30 / 31–70 / 71–90 / 90+ respectively. This function SHALL NOT read or
depend on any owned skill.

#### Scenario: A level-30 entity is 術師
- **WHEN** `magic_rank_title(entity)` is called on an entity with `magic_level.value == 30`
- **THEN** it returns `"術師"`

#### Scenario: A level-873 entity is 主宰 regardless of owned skills
- **WHEN** `magic_rank_title(entity)` is called on an entity with `magic_level.value == 873` and no
  owned mastery skills
- **THEN** it returns `"主宰"`

### Requirement: can_cast_spell_tier gates casting by element-effective numeric level, overridden by direct mastery ownership
`world/rules/progression.py` SHALL define `can_cast_spell_tier(entity, element: str, tier: str) ->
bool`, returning `True` if the entity's element-effective magic level meets `tier`'s band threshold,
or `True` unconditionally if `f"{element}_mastery"` appears in `entity.skills.owned_keys()` (checked
via direct ownership only, not via `entity.skills.conferred_grants()`). The element-effective magic
level SHALL be `floor(entity.traits.magic_level.value * element_affinity_multiplier(entity,
element))`, so a favored element unlocks tiers earlier and a non-favored element unlocks them later.
The element SHALL be validated against `ELEMENT_REGISTRY` before either check, and an unrecognized
element key SHALL raise `ValueError` even when the entity owns a fabricated `<element>_mastery`.
Consumers that must not propagate exceptions (the monster behaviour policy) SHALL treat a
`ValueError` from this function as a denied cast. This function SHALL NOT consult `magic_rank_title`.
The threshold table is 學徒 0 / 術師 16 / 大師 31 / 賢者 71 / 主宰 91: the lore's "90+" 主宰 display
band resolves at 91 mechanically, so a human at the magic cap (90) without a favored affinity or
direct mastery ownership reads as 賢者 and never satisfies the 主宰 gate.

#### Scenario: A low-level entity without mastery cannot cast a high-tier spell
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on a neutral entity (no
  affinities) with `magic_level.value == 30` and no owned `fire_mastery`
- **THEN** it returns `False`

#### Scenario: An entity with the element's mastery skill can cast any tier of that element
- **WHEN** `can_cast_spell_tier(entity, "wind", "主宰")` is called on an entity with
  `magic_level.value == 1` and `entity.skills.owned_keys()` containing `"wind_mastery"`
- **THEN** it returns `True`

#### Scenario: A conferred mastery grant does not satisfy the gate
- **WHEN** `can_cast_spell_tier(entity, "fire", "主宰")` is called on an entity whose only
  relationship to `fire_mastery` is a `ConferredSkillGrant` referencing it (not direct ownership)
- **THEN** it returns `False` unless the entity's own element-effective magic level independently
  meets the tier

#### Scenario: A favored element unlocks a tier earlier than the base threshold
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on an entity with
  `entity.db.affinity_elements == ["fire"]` and `magic_level.value == 29`
- **THEN** it returns `True`, because `floor(29 * 1.1) == 31` meets the 大師 threshold

#### Scenario: A non-favored element unlocks a tier later than the base threshold
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on an entity with
  `entity.db.affinity_elements == ["wind"]` and `magic_level.value == 34`
- **THEN** it returns `False`, because `floor(34 * 0.9) == 30` is below the 大師 threshold, while the
  same entity at `magic_level.value == 35` returns `True`

#### Scenario: A human can reach 主宰 only for a favored element
- **WHEN** a human entity (`magic_level.max == 90`) with `entity.db.affinity_elements == ["fire"]`
  reaches `magic_level.value == 83`
- **THEN** `can_cast_spell_tier(entity, "fire", "主宰")` returns `True`
  (`floor(83 * 1.1) == 91`), while `can_cast_spell_tier(entity, "wind", "主宰")` for the same entity
  returns `False` at every level up to the cap (`floor(90 * 0.9) == 81`)

#### Scenario: An unknown element fails closed even with a fabricated mastery
- **WHEN** `can_cast_spell_tier(entity, "not_an_element", "學徒")` is called on an entity that owns
  a skill key `"not_an_element_mastery"`
- **THEN** it raises `ValueError`, and the monster behaviour policy consuming the function treats
  that cast as denied rather than raising
