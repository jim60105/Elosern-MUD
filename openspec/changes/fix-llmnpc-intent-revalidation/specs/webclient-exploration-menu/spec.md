## ADDED Requirements

### Requirement: Freeform-talk completion rechecks presence before applying intents

The freeform-talk adapter SHALL re-run the co-location and interactability checks when the deferred reply settles, before any intent application, and SHALL return a clear stale-completion result when the checks fail.

#### Scenario: Deferred reply after the player moved is discarded

- **WHEN** the player sends freeform talk and moves away before the reply arrives
- **THEN** the adapter shows the speech, discards the intent, and reports the stale context to the player
