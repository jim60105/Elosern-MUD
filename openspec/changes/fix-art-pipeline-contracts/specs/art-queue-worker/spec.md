## ADDED Requirements

### Requirement: In-flight generation exposes a wire-stable status

The art presenter SHALL normalize the internal `in_progress` record status to a wire-accepted value (`pending`) so a panel snapshot taken while a worker holds a claim never fails validation.

#### Scenario: Snapshot during generation shows a valid pending state

- **WHEN** a worker has claimed a record (status `in_progress`) and a full art snapshot is requested
- **THEN** the panel payload carries the wire-stable `pending` status (or an explicitly supported generating status) and the panel renders normally

#### Scenario: Settled statuses pass through unchanged

- **WHEN** a record is `missing`, `pending`, `failed`, or `done`
- **THEN** the presenter emits that status without normalization
