## Purpose

Keeps private story-direction drafts and explicitly confirmed versioned requests separate from in-world knowledge and deterministic outcomes.

## ADDED Requirements

### Requirement: Creative discussion remains private authoring data

Drafts/requests SHALL express themes, atmosphere, participants, emphasis and exclusions for new stories or existing-thread direction. They SHALL NOT rewrite committed history/personality/outcomes or grant clues, items, progress, stats, skills, buffs, codex unlocks or NPC knowledge. Invalid directions SHALL receive a concrete reason and remain unconfirmed without silent substitution.

#### Scenario: Incompatible history rewrite
- **WHEN** a player asks to replace a committed event
- **THEN** validation explains the conflict and preserves an unconfirmed draft

#### Scenario: Unrelated new storyline
- **WHEN** a player requests a new direction unrelated to prior experience
- **THEN** the draft can describe it but it is eligible only after explicit confirmation

#### Scenario: NPC recall after private discussion
- **WHEN** an NPC retrieval runs after the player saved a creative draft
- **THEN** private discussion is absent from cognition

### Requirement: Explicit version confirmation submits once

Confirmation SHALL create a versioned request, deterministically validate its direction and schedule only that confirmed valid version. Draft preservation SHALL not submit. Duplicate confirmation/restart SHALL not duplicate submission; editing a version SHALL require new confirmation. Deterministic confirmation validation SHALL remain available offline.

#### Scenario: Duplicate confirmation
- **WHEN** the same valid version is confirmed twice across reconnect
- **THEN** one request/submission identity exists

#### Scenario: Draft departure
- **WHEN** the player preserves an incomplete discussion as a draft
- **THEN** no director work is scheduled

#### Scenario: Offline valid confirmation
- **WHEN** all generation services are disabled and a saved valid version is confirmed
- **THEN** deterministic validation and one durable request complete without a model call

