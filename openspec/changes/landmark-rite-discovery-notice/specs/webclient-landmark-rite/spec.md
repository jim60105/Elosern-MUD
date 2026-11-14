# Spec Delta

## ADDED Requirements

### Requirement: The rite stage names a newly lit district
After a rite whose result marks the district's first completion finishes playing, the rite stage's message window SHALL show one line naming the newly lit district until the player leaves the stage or performs again. A repeated rite SHALL add no such line.

#### Scenario: First completion
- **WHEN** a rite result marked as a first completion finishes playing
- **THEN** the message window shows the guardian's form and one further line naming the district

#### Scenario: Repeat and re-entry
- **WHEN** a rite result not marked as a first completion finishes, or the player leaves and re-enters the stage
- **THEN** only the guardian's form is shown
