## ADDED Requirements

### Requirement: Dispatch rejects no-puppet actions with a bounded response

The action dispatcher SHALL return a bounded rejection (stable code, no character data) for actions submitted without a puppeted actor, instead of silently dropping them.

#### Scenario: No-puppet action returns a stable rejection

- **WHEN** `ui_action` is dispatched while `session.puppet` is None
- **THEN** the client receives a rejection with a stable code and no character state
