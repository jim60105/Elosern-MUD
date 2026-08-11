## ADDED Requirements

### Requirement: Startup restores combat sessions before wilderness population reconciliation

The deterministic startup sequence SHALL restore persisted combat sessions (or otherwise protect their recorded participants) before any wilderness population reconciliation can delete or replace a monster referenced by an active session, so a committed terminal outcome is never converted into a defeat by the reconciliation.

#### Scenario: Defeated population monster survives until session restore

- **WHEN** a restart follows a terminal round against a wilderness population monster whose session was not yet settled
- **THEN** session restoration runs before population reconciliation and settles the committed outcome, and the reconciliation does not delete or respawn the recorded participant first
