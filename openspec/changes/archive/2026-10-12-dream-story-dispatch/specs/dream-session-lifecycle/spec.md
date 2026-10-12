# Spec Delta

## ADDED Requirements

### Requirement: Valid confirmation closes the session without awaiting dispatch

A valid explicit version confirmation SHALL atomically save the request, create/get its unique dispatch record, preserve source linkage and close the session as confirmed. The pump SHALL be notified only after commit as a wake-up hint. Waking response SHALL finish without a model await or clock advance; a rollback SHALL leave no confirmed session with missing request/work.

#### Scenario: Real confirmation with an unresolved model
- **WHEN** confirmation uses the real dream surface while the injected background model response remains unresolved
- **THEN** the player has returned to waking play, exactly one immutable request/work exists and original sleep tick/gauges and completed exchange count are unchanged

#### Scenario: Work persistence fails
- **WHEN** work creation fails in the confirmation transaction
- **THEN** request creation and confirmed closure roll back together and no pump notification runs

#### Scenario: Lost wake-up hint
- **WHEN** confirmation commits but its pump notification is lost
- **THEN** startup or a later notification can find the saved queued work without re-confirming or scanning historical requests
