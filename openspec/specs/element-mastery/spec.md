## Purpose

Element mastery ties the display rank title and the mechanical cast gate to an
entity's numeric magic level, with direct ownership of an element's mastery
skill overriding the gate. Everything here is a pure, side-effect-free query;
nothing in this capability writes game state.

## Requirements

### Requirement: Mastery ownership entitles freeform scaling of the element's eligible spells
`world/rules/progression.py` SHALL define `freeform_mastery_entitled(entity, element: str) -> bool`
as a pure, side-effect-free entitlement query that validates `element` against `ELEMENT_REGISTRY`
first (an unrecognized element SHALL raise `ValueError` even when the entity owns a fabricated
`<element>_mastery`), then returns whether `f"{element}_mastery"` appears in
`entity.skills.owned_keys()` (direct ownership only, never `conferred_grants()`). It SHALL grant no
scale by itself. `world/rules/progression.py` SHALL define `freeform_scales_for(entity, skill) ->
tuple[float, ...]` as the single ladder authority: it returns `()` for a skill with no element or an
entity that is not `freeform_mastery_entitled` for that skill's element, and otherwise the ascending
rungs of the `progression.yaml` `freeform_scale_ladder` whose `min_level` the entity's OWN
`skill_proficiency_level` for THAT SKILL reaches — 0.25 unconditionally for an entitled actor, 0.5
at level >= 1, 1.0 at >= 3, 2.0 at >= 6, 4.0 at >= 10; a skill whose derived tip cap is below 10 can
never include 4.0. The skill anchoring is the contract: proficiency in a sibling skill of the same
element SHALL NOT raise the returned set, so no consumer can advertise a rung the resolver would
reject. Neither function SHALL write any entity state. The empty tuple is the entitlement signal
consumed by the freeform-casting gate: without it, every non-`1.0` scale for that skill is forbidden.

#### Scenario: A mastery holder's scale set follows the cast skill's proficiency ladder
- **WHEN** `freeform_scales_for(entity, skill)` is called for a fire skill on an entity whose
  `owned_keys()` contains `"fire_mastery"` and whose proficiency in THAT skill reaches 10
- **THEN** it returns `(0.25, 0.5, 1.0, 2.0, 4.0)` in ascending order; at level 0 it returns
  `(0.25,)`, at level 1 `(0.25, 0.5)`, at level 3 `(0.25, 0.5, 1.0)`, at level 6
  `(0.25, 0.5, 1.0, 2.0)`

#### Scenario: A sibling skill's proficiency never raises the set
- **WHEN** the entity holds level-10 proficiency in one fire skill and level 0 in another
- **THEN** `freeform_scales_for` returns `(0.25,)` for the level-0 skill regardless of the sibling

#### Scenario: An entity without mastery receives an empty set
- **WHEN** `freeform_scales_for(entity, skill)` is called on an entity without the element's
  mastery, including one with a high magic level and one holding only a `ConferredSkillGrant`
  referencing `<element>_mastery`
- **THEN** it returns `()` in both cases

#### Scenario: An unknown element fails closed
- **WHEN** `freeform_mastery_entitled(entity, "not_an_element")` is called on an entity owning
  `"not_an_element_mastery"`
- **THEN** it raises `ValueError` and writes no state
