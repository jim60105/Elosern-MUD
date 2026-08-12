## ADDED Requirements

### Requirement: All eight elements have a mastery skill
`SKILL_REGISTRY` SHALL contain `water_mastery`, `earth_mastery`, `lightning_mastery`, and
`ice_mastery`, each `PASSIVE`, `TargetSpec.NONE`, with `element` set to the corresponding
`world.lore.elements.ELEMENT_REGISTRY` entry and `effects=["element_mastery_rank:主宰"]`, matching the
existing four mastery skills' (`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery`) shape
exactly.

#### Scenario: All eight elemental-mastery skills are present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains a `PASSIVE` entry for fire, water, wind, earth, lightning, ice, light, and dark
  mastery, each with `element` set to the corresponding `ELEMENT_REGISTRY` entry
