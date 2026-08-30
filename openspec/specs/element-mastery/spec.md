## Purpose

Element mastery ties the display rank title and the mechanical cast gate to an
entity's numeric magic level, with direct ownership of an element's mastery
skill overriding the gate. Everything here is a pure, side-effect-free query;
nothing in this capability writes game state.

## Requirements

### Requirement: can_cast_spell_tier gates casting by element-effective numeric level, overridden by direct mastery ownership
`world/rules/progression.py` SHALL define `can_cast_spell_tier(entity, element: str, tier: str) ->
bool`, returning `True` if the entity's element-effective magic level meets `tier`'s band threshold,
or `True` unconditionally if `f"{element}_mastery"` appears in `entity.skills.owned_keys()` (checked
via direct ownership only, not via `entity.skills.conferred_grants()`). The element-effective magic
level SHALL be `floor(entity.traits.magic_power.value * element_affinity_multiplier(entity,
element))`, so a favored element unlocks tiers earlier and a non-favored element unlocks them later.
The element SHALL be validated against `ELEMENT_REGISTRY` before either check, and an unrecognized
element key SHALL raise `ValueError` even when the entity owns a fabricated `<element>_mastery`.
The threshold table is 學徒 0 / 術師 16 / 大師 31 / 賢者 71 / 主宰 91: the lore's "90+" 主宰 display
band resolves at 91 mechanically, so a human at the race ``magic_power`` band ceiling (90) without a
favored affinity or direct mastery ownership reads as 賢者 and never satisfies the 主宰 gate.

#### Scenario: A low-level entity without mastery cannot cast a high-tier spell
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on a neutral entity (no
  affinities) with `magic_power.value == 30` and no owned `fire_mastery`
- **THEN** it returns `False`

#### Scenario: An entity with the element's mastery skill can cast any tier of that element
- **WHEN** `can_cast_spell_tier(entity, "wind", "主宰")` is called on an entity with
  `magic_power.value == 1` and `entity.skills.owned_keys()` containing `"wind_mastery"`
- **THEN** it returns `True`

#### Scenario: A conferred mastery grant does not satisfy the gate
- **WHEN** `can_cast_spell_tier(entity, "fire", "主宰")` is called on an entity whose only
  relationship to `fire_mastery` is a `ConferredSkillGrant` referencing it (not direct ownership)
- **THEN** it returns `False` unless the entity's own element-effective magic level independently
  meets the tier

#### Scenario: A favored element unlocks a tier earlier than the base threshold
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on an entity with
  `entity.db.affinity_elements == ["fire"]` and `magic_power.value == 29`
- **THEN** it returns `True`, because `floor(29 * 1.1) == 31` meets the 大師 threshold

#### Scenario: A non-favored element unlocks a tier later than the base threshold
- **WHEN** `can_cast_spell_tier(entity, "fire", "大師")` is called on an entity with
  `entity.db.affinity_elements == ["wind"]` and `magic_power.value == 34`
- **THEN** it returns `False`, because `floor(34 * 0.9) == 30` is below the 大師 threshold, while the
  same entity at `magic_power.value == 35` returns `True`

#### Scenario: A human can reach 主宰 only for a favored element
- **WHEN** a human entity (whose `RACE_REGISTRY["human"].static_baseline.magic_power` band ceiling
  is `90`, so its static `magic_power.value` is at most 90) with
  `entity.db.affinity_elements == ["fire"]` reaches `magic_power.value == 83`
- **THEN** `can_cast_spell_tier(entity, "fire", "主宰")` returns `True`
  (`floor(83 * 1.1) == 91`), while `can_cast_spell_tier(entity, "wind", "主宰")` for the same entity
  returns `False` at every value up to the band ceiling (`floor(90 * 0.9) == 81`)

#### Scenario: An unknown element fails closed even with a fabricated mastery
- **WHEN** `can_cast_spell_tier(entity, "not_an_element", "學徒")` is called on an entity that owns
  a skill key `"not_an_element_mastery"`
- **THEN** it raises `ValueError`, and the monster behaviour policy consuming the function treats
  that cast as denied rather than raising

### Requirement: can_cast_skill is the shared side-effect-free cast-eligibility predicate
`world/rules/progression.py` SHALL define `can_cast_skill(entity, skill) -> bool`, a pure,
side-effect-free query returning `True` when the given skill is not an elemental spell
(`spell_tier_for(skill)` returns `None`), and otherwise delegating to `can_cast_spell_tier(entity,
skill.element.key, tier)` for the skill's derived tier. A `ValueError` raised by either underlying
query (malformed MP cost outside every tier band, an unrecognized element key, or an unknown tier)
SHALL be converted to `False` — the predicate fails closed and never propagates. `ActionResolver`'s
ownership step and every deterministic AI combat policy SHALL consume this single predicate for
spell-tier eligibility; the predicate SHALL NOT read any display title, consult
`conferred_grants()`, or write any entity state.

#### Scenario: A non-elemental skill always passes the gate
- **WHEN** `can_cast_skill(entity, basic_attack)` is called on any entity that owns `basic_attack`
  (an ACTIVE skill with no MP cost and therefore no tier)
- **THEN** it returns `True` regardless of the entity's magic level

#### Scenario: An over-tier elemental spell fails closed
- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with
  `magic_power.value == 15`, no declared affinities, and no owned `fire_mastery` (firestorm's 30 MP
  cost derives the 術師 tier, and `floor(15 * 1.0) == 15` is below the 16 threshold)
- **THEN** it returns `False`, exactly as `ActionResolver` would reject the cast

#### Scenario: The mastery override unlocks a spell through the predicate
- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with `magic_power.value == 1`
  whose `owned_keys()` contains `"fire_mastery"`
- **THEN** it returns `True`

#### Scenario: A favored affinity boundary passes through the predicate
- **WHEN** `can_cast_skill(entity, firestorm)` is called on an entity with `magic_power.value == 15`
  and `entity.db.affinity_elements == ["fire"]`
- **THEN** it returns `True`, because `floor(15 * 1.1) == 16` meets the 術師 threshold

#### Scenario: A malformed elemental spell is denied, not raised
- **WHEN** `can_cast_skill(entity, skill)` is called for an elemental spell whose MP cost is
  non-positive or outside every tier band (so `spell_tier_for` raises `ValueError`), or whose
  element is unrecognized
- **THEN** it returns `False` instead of raising, so policy and preview consumers never see an
  exception from a content-authoring error. (A spell with no MP cost at all derives no tier and is
  not gated — `basic_attack` carries an element but is never blocked.)

### Requirement: Mastery ownership entitles freeform scaling of the element's eligible spells
`world/rules/progression.py` SHALL define `freeform_scales_for(entity, element: str) ->
tuple[float, ...]` as a pure, side-effect-free query that validates `element` against
`ELEMENT_REGISTRY` first (an unrecognized element SHALL raise `ValueError` even when the entity owns
a fabricated `<element>_mastery`), then returns the ascending `freeform_cast_scales` set
(`0.25, 0.5, 1.0, 2.0, 4.0`) when `f"{element}_mastery"` appears in `entity.skills.owned_keys()`
(direct ownership only, never `conferred_grants()`), and an empty tuple otherwise. The function
SHALL NOT write any entity state. The empty tuple is the entitlement signal consumed by the
freeform-casting gate: without it, every non-`1.0` scale for that element is forbidden.

#### Scenario: A mastery holder receives the full scale set
- **WHEN** `freeform_scales_for(entity, "wind")` is called on an entity whose `owned_keys()`
  contains `"wind_mastery"`
- **THEN** it returns `(0.25, 0.5, 1.0, 2.0, 4.0)` in ascending order

#### Scenario: An entity without mastery receives an empty set
- **WHEN** `freeform_scales_for(entity, "wind")` is called on an entity without `wind_mastery`,
  including one with a high magic level and one holding only a `ConferredSkillGrant` referencing
  `wind_mastery`
- **THEN** it returns `()` in both cases

#### Scenario: An unknown element fails closed
- **WHEN** `freeform_scales_for(entity, "not_an_element")` is called on an entity owning
  `"not_an_element_mastery"`
- **THEN** it raises `ValueError` and writes no state
