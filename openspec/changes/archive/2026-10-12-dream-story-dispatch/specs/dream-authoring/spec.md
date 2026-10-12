# Spec Delta

## MODIFIED Requirements

### Requirement: Explicit version confirmation submits once

Confirmation SHALL validate and freeze the shown direction/version and atomically create/get its unique request and dispatch work identity with source linkage. Draft preservation SHALL not submit. Duplicate confirmation/restart SHALL not duplicate submission or work; editing a version SHALL require new confirmation. Deterministic validation SHALL remain available offline, with unavailable generation waiting after confirmation.

#### Scenario: Duplicate confirmation
- **WHEN** the same valid version is confirmed twice across reconnect
- **THEN** one request/submission identity and one linked dispatch record exist

#### Scenario: Draft departure
- **WHEN** the player preserves an incomplete discussion as a draft
- **THEN** no director work is scheduled

#### Scenario: Offline valid confirmation
- **WHEN** all generation services are disabled and a saved valid version is confirmed
- **THEN** deterministic validation and one durable request/work complete without a model call and required unavailable generation becomes waiting_service

## ADDED Requirements

### Requirement: Confirmation freezes visible bounded experience requirements

The collaborator draft SHALL propose bounded experience requirements alongside the original summary, including explicit place, new-role and private-commission needs where requested. Their readable meaning SHALL appear before confirmation and be frozen with the version. Deterministic completeness checks SHALL use those shown fields and SHALL NOT claim to prove arbitrary natural-language intent through hidden late interpretation.

#### Scenario: Motivating direction keeps executable requirements
- **WHEN** the player discusses the direction about meeting a girl at the south gate and helping her find her mother
- **THEN** the draft shows its named-place, new-character and private escort-commission requirements and the confirmed version retains exactly the displayed requirements

#### Scenario: Edited summary needs a reviewed version
- **WHEN** the player changes the direction after requirements were proposed
- **THEN** the surface presents the current version's corresponding requirements before confirmation and stale unseen requirements cannot be frozen silently

#### Scenario: No invented world history
- **WHEN** a direction claims a past player action or hidden NPC knowledge
- **THEN** authoring remains private source data and no progress, committed event, personality or NPC memory changes through confirmation
