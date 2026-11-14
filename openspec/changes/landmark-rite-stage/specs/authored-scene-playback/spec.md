# Spec Delta

## ADDED Requirements

### Requirement: Rite deliveries play through the shared scene player
A landmark rite delivery SHALL be rendered by the same manual scene player as dialogue scenes, with the acting body as the actor name and the guardian as the host name, and SHALL add no second pager, typewriter or renderer.

#### Scenario: Rite scene attribution
- **WHEN** a rite delivery with narration, an actor line and a host line plays
- **THEN** each line advances only by explicit activation, the actor line shows the delivery's actor name, the host line shows the guardian's name and narration shows no speaker

#### Scenario: Finish returns control
- **WHEN** the last page is acknowledged
- **THEN** the scene finishes once and the rite panel returns
