## ADDED Requirements

### Requirement: Beat-scoped blueprint generation does not substitute template filler

A beat-scoped ScenarioDirector entry point SHALL accept a validated quest beat and permitted immutable narrative context, use the existing client/profile/guardrail/schema and semantic validators, and return a context-fitting QuestBlueprint proposal or a no-content outcome. Disabled transport, exhausted validation and context misfit SHALL NOT substitute a generic template. The existing generate_quest_blueprint entry point SHALL retain its generic authored-template degradation contract.

#### Scenario: Beat misfit does not draw template
- **WHEN** a schema-valid beat blueprint fails its narrative/rank/issuer/anchor fitness gate
- **THEN** the beat entry point yields no content and no template draw

#### Scenario: Generic degradation still works
- **WHEN** the generic non-beat entry point runs with disabled generation
- **THEN** it draws a compatible authored template as before

