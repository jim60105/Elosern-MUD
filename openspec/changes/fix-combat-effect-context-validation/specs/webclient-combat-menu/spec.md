## ADDED Requirements

### Requirement: Combat menu availability reflects handler context

A skill SHALL be marked unavailable in the combat menu when the session's `event_context` cannot supply every context key its effects require; the menu SHALL never advertise a skill that preflight would reject for missing context.

#### Scenario: Context-less skills are disabled

- **WHEN** the combat menu renders while the session context lacks disguise/dominion keys
- **THEN** `status_disguise` and `dominion_art` appear unavailable (disabled), and submitting them is rejected before initiative
