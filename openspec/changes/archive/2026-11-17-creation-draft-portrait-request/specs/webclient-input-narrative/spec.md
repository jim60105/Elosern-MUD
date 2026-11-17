# Spec Delta

## ADDED Requirements

### Requirement: Creation portrait requests echo a bounded action label
An admitted `creation.portrait.generate` SHALL append one bounded literal action-label line through the existing mutation echo path. Local portrait browsing or opening the drawer SHALL append none. Prompt text and draft identity values SHALL NOT enter that echo.

#### Scenario: One admitted request echoes once
- **WHEN** a portrait request dispatches and its result later rejects or succeeds
- **THEN** its one action-label echo remains, contains no prompt or draft identity text, and neither replay nor result observation appends a second echo

#### Scenario: Local and blocked interactions stay silent
- **WHEN** the player opens/closes the drawer or the shared dispatch gate refuses admission
- **THEN** no request echo is appended and no raw text command is submitted
