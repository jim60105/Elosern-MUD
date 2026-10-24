# Spec Delta

## MODIFIED Requirements

### Requirement: Valid confirmation closes the session without awaiting dispatch
A valid explicit version confirmation SHALL atomically save the request, create/get unique dispatch work, preserve source linkage and close as confirmed. The pump SHALL be notified only after commit. Narrative confirmation SHALL await no model and write no clock; its outer rules consumer SHALL then continue only the linked sleep receipt's uncommitted interval or publish a real interruption. Rollback SHALL leave no confirmed session with missing request/work.

#### Scenario: Real confirmation with an unresolved model
- **WHEN** the real pre-recovery dream surface confirms while background generation remains unresolved
- **THEN** one immutable request/work and confirmed closure exist, exchange count is unchanged, and only the outer rules sleep continuation advances the remaining accepted owner sleep once or reports its genuine interruption before normal waking actions

#### Scenario: Work persistence fails
- **WHEN** work creation fails inside confirmation
- **THEN** request and confirmed closure roll back together and no pump notification or recovery continuation is committed

#### Scenario: Lost wake-up hint
- **WHEN** confirmation commits but its pump notification is lost
- **THEN** startup or a later notification finds queued work without re-confirming, scanning historical requests or re-settling sleep

#### Scenario: Narrative closure and physical continuation have distinct ownership
- **WHEN** narrative confirmation commits and a later rules continuation interval fails
- **THEN** request/work remain truthful, failed interval writes restore, durable same-receipt continuation intent remains retryable and reconnect never opens another sleep
