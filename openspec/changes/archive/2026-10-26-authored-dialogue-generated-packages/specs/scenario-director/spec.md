# Spec Delta

## ADDED Requirements

### Requirement: Dream scene generation proposes the complete shared dialogue schema
The production dream scene route SHALL prompt for and validate complete shared scenes, variants, qualification/refusal, chains and permitted references in the extended package schema. It SHALL preserve those declarations through captured checkpoints into deterministic publication. LLM output SHALL remain proposal data only, with existing bounded failure/no-content behavior and no source-file writes.

#### Scenario: Real dream dispatch publishes playable dialogue
- **WHEN** a confirmed dream request requiring a conversable generated role passes through the production story/scenario dispatch with injected deterministic clients
- **THEN** its rendered scene-specific prompt and inline schema describe the shared scene contract, its checkpoint preserves that content, and deterministic publication creates one immutable package whose materialized host uses the shared scene engine

#### Scenario: Invalid generated scene has no publication
- **WHEN** generated output uses old response-only topics, unknown conditions, foreign references, executable fields, unauthorized effects or exceeded bounds
- **THEN** bounded validation/refusal produces no package, arrangement or static registry mutation

#### Scenario: Generic blueprint behavior is preserved
- **WHEN** the ordinary non-dream QuestBlueprint route degrades or a dream scene service is disabled
- **THEN** ordinary generation retains its existing authored-template degradation and dream scene generation retains no-content or waiting-service behavior without template substitution
