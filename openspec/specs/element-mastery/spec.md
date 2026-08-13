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

### Requirement: can_cast_spell_tier gates casting by numeric level, overridden by direct mastery ownership
`world/rules/progression.py` SHALL define `can_cast_spell_tier(entity, element: str, tier: str) ->
bool`, returning `True` if `entity.traits.magic_level.value` meets `tier`'s band threshold, or `True`
unconditionally if `f"{element}_mastery"` appears in `entity.skills.owned_keys()` (checked via direct
ownership only, not via `entity.skills.conferred_grants()`). This function SHALL NOT consult
`magic_rank_title`. The threshold table is 學徒 0 / 術師 16 / 大師 31 / 賢者 71 / 主宰 91: the lore's
"90+" 主宰 display band resolves at 91 mechanically, so a human at the magic cap (90) reads as 賢者
and never satisfies the 主宰 gate.

#### Scenario: A low-level entity without mastery cannot cast a high-tier spell
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on an entity with
  `magic_level.value == 30` and no owned `fire_mastery`
- **THEN** it returns `False`

#### Scenario: An entity with the element's mastery skill can cast any tier of that element
- **WHEN** `can_cast_spell_tier(entity, "wind", "主宰")` is called on an entity with
  `magic_level.value == 1` and `entity.skills.owned_keys()` containing `"wind_mastery"`
- **THEN** it returns `True`

#### Scenario: A conferred mastery grant does not satisfy the gate
- **WHEN** `can_cast_spell_tier(entity, "fire", "主宰")` is called on an entity whose only relationship
  to `fire_mastery` is a `ConferredSkillGrant` referencing it (not direct ownership)
- **THEN** it returns `False` unless the entity's own numeric magic level independently meets the tier
