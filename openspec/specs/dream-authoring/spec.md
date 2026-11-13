# dream-authoring Specification

## Purpose
Keeps private story-direction drafts and explicitly confirmed versioned requests separate from in-world knowledge and deterministic outcomes.

## Requirements

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

### Requirement: Confirmation freezes visible bounded experience requirements

The collaborator SHALL propose bounded experience requirements as part of the proposal. Their readable meaning SHALL appear before confirmation and be frozen with the version. A dream confirmation SHALL save the submitted finalized proposal as the shown version and confirm exactly that version. Deterministic completeness checks SHALL use those shown fields and SHALL NOT claim to prove arbitrary natural-language intent through hidden late interpretation.

#### Scenario: Motivating direction keeps executable requirements
- **WHEN** the collaborator's edits give the proposal a named-place, a new-character and a private-commission requirement and the player finalizes and confirms without changing them
- **THEN** the confirmed version retains exactly those requirement rows

#### Scenario: Edited summary needs a reviewed version
- **WHEN** the player changes the summary or the requirement rows in the finalized stage and confirms
- **THEN** the submitted form is saved as the reviewed version and the confirmed version carries exactly the submitted summary and rows under that one version identity, with no model call and no separate save step

#### Scenario: A stored version cannot be confirmed with rows it never showed
- **WHEN** the session confirmation operation is given a requirement-bearing direction whose version identity or rows differ from the saved draft version
- **THEN** it is refused as stale and nothing is submitted

#### Scenario: An invalid submitted proposal stays a draft
- **WHEN** a finalized confirmation submits a proposal that deterministic validation refuses
- **THEN** the refusal names the concrete reason, the submitted proposal is kept as the unconfirmed draft and no request is created

#### Scenario: No invented world history
- **WHEN** a direction claims a past player action or hidden NPC knowledge
- **THEN** authoring remains private source data and no progress, committed event, personality or NPC memory changes through confirmation

#### Scenario: Requested needs are part of the proposal
- **WHEN** the collaborator proposes bounded experience requirements for a direction
- **THEN** the proposal includes explicit place, new-role and private-commission needs where requested
