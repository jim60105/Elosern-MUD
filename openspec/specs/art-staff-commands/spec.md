# art-staff-commands Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
## Requirements
### Requirement: @art status lists and filters records without leaking sensitive data
`commands/art.py::CmdArtStatus` (`@art status [scene|portrait]`) SHALL list asset records filtered by
subject kind, showing subject key, status, aspect ratio, attempt count, and bounded error code. Output
SHALL NOT include persona text, prompt content, absolute filesystem paths, or the store root.

#### Scenario: Staff can list scene and portrait records
- **WHEN** staff runs `@art status` and `@art status portrait`
- **THEN** scene and portrait records are listed with their statuses, and no persona text or absolute
  path appears in the output

#### Scenario: Non-staff cannot use the command
- **WHEN** a player without staff access runs any `@art` subcommand
- **THEN** the command is denied with a permission error

### Requirement: @art run drains the shared queue now with an optional limit
`commands/art.py::CmdArtRun` (`@art run [--limit N]`) SHALL drain pending records through the shared
worker boundary asynchronously, never blocking play, honoring the queue lock, and SHALL report how
many jobs were dispatched (or the named error when the worker cannot start).

#### Scenario: A bounded drain dispatches pending jobs
- **WHEN** staff runs `@art run --limit 5` with pending records present
- **THEN** at most five pending records are dispatched through the worker and the command reports the
  count dispatched

### Requirement: @art retry re-enqueues failed records
`commands/art.py::CmdArtRetry` (`@art retry`) SHALL re-enqueue every `failed` record to `pending`
under the queue lock and SHALL report the number re-enqueued.

#### Scenario: Failed records are re-enqueued
- **WHEN** staff runs `@art retry` with failed records present
- **THEN** each failed record becomes `pending` and the command reports the re-enqueued count

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A valid key SHALL reset the record to `pending` under the queue lock, preserve
the prior valid output, and SHALL be the only way an ordinary-lifecycle pass can force regeneration.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:forest_path`
- **THEN** the scene record becomes `pending`, its prior valid output is preserved, and a regeneration
  is queued under the queue lock

#### Scenario: An invalid key is rejected with no record change
- **WHEN** staff runs `@art requeue` with a malformed or unknown full subject key
- **THEN** a named error is returned and no record is changed

### Requirement: Players have no access to any art control
No `@art` subcommand SHALL be available to ordinary players, and no player-triggered retry or
regeneration surface SHALL exist.

#### Scenario: All subcommands require staff
- **WHEN** every `@art` subcommand's access is exercised with a non-staff caller
- **THEN** each is denied and no queue, store, or worker operation runs

