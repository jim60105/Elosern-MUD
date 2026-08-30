## Purpose

Element mastery ties the display rank title and the mechanical cast gate to an
entity's numeric magic level, with direct ownership of an element's mastery
skill overriding the gate. Everything here is a pure, side-effect-free query;
nothing in this capability writes game state.

## Requirements

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
