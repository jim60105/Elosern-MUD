# Spec Delta

## MODIFIED Requirements

### Requirement: Confirmation freezes visible bounded experience requirements

The collaborator SHALL propose bounded experience requirements as part of the proposal, including explicit place, new-role and private-commission needs where requested. Their readable meaning SHALL appear before confirmation and be frozen with the version. A dream confirmation SHALL save the submitted finalized proposal as the shown version and confirm exactly that version. Deterministic completeness checks SHALL use those shown fields and SHALL NOT claim to prove arbitrary natural-language intent through hidden late interpretation.

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
