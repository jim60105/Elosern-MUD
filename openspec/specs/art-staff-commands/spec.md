# art-staff-commands Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
## Requirements
### Requirement: @art status lists and filters records without leaking sensitive data
`commands/art.py::CmdArtStatus` (`@art status [scene|portrait]`) SHALL list asset records filtered by
subject kind, showing subject key, status, aspect ratio, attempt count, bounded error code, and —
only when the record carries one — the persisted generation seed. Output
SHALL NOT include persona text, prompt content, absolute filesystem paths, or the store root.

#### Scenario: Staff can list scene and portrait records
- **WHEN** staff runs `@art status` and `@art status portrait`
- **THEN** scene and portrait records are listed with their statuses, and no persona text or absolute
  path appears in the output

#### Scenario: A completed record shows its generation seed
- **WHEN** a `done` record persists seed `42` and staff runs `@art status`
- **THEN** that record's line includes the seed `42`

#### Scenario: A seedless record shows no seed field
- **WHEN** a record has no persisted seed (missing, pending, or a done record generated without a
  server-reported seed)
- **THEN** its line shows no seed value and the listing renders normally

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

### Requirement: @art options lists the live server's selectable option names
`commands/art.py` SHALL provide `@art options <models|samplers|schedulers|styles|modules>`
restricted to `Developer`, which performs one bounded read-only enumeration of the configured
sd-webui server (no queue, record, or setting mutation) and prints the exact selectable names,
one per line, with a header naming the option kind and total count. A missing, unknown, or
multi-word argument SHALL be rejected with the usage line and no request sent. Any enumeration
failure SHALL print the named error code and no partial list. Display names SHALL be bounded to
256 code points per line. The output SHALL NOT include the configured credentials or any
`Authorization` material, and SHALL name at most the server host (never a URL containing
userinfo).

#### Scenario: Staff lists the server's samplers
- **WHEN** staff runs `@art options samplers` against a reachable server returning two samplers
- **THEN** both names are listed one per line under a header with the kind and count, and no
  record changed

#### Scenario: An unreachable server yields the named code only
- **WHEN** staff runs `@art options models` while the server is unreachable
- **THEN** the output contains the named `SDError` code, no list, and no partial data

#### Scenario: An invalid argument is rejected without a request
- **WHEN** staff runs `@art options` with no argument or an unknown kind
- **THEN** the usage line is printed and no HTTP request is attempted

#### Scenario: Non-staff cannot enumerate
- **WHEN** a non-Developer caller runs `@art options models`
- **THEN** the command is denied and no request is attempted

### Requirement: @art health reports server reachability, scheduler state, queue counts, and output policy
`commands/art.py` SHALL provide `@art health` restricted to `Developer`, which performs exactly
one forced connectivity probe and prints four sections in fixed order: (1) server reachability —
`reachable` or `unreachable` with the named error code and that the check ran just now; (2) the
effective scheduler state (`ART_SCHEDULER_ENABLED` with interval seconds and limit); (3) exact
record counts by status (`pending`, `in_progress`, `failed`, `done`); (4) the effective output
policy (`ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`, and whether generation-metadata
preservation is on). The command SHALL mutate no record, queue entry, or setting, and its output
SHALL NOT contain credentials, URL userinfo, absolute paths, prompt text, or persona text.

#### Scenario: Health shows a reachable server with full dashboard state
- **WHEN** staff runs `@art health` against a reachable server with the scheduler enabled and a
  mixed-status record store
- **THEN** the output shows the forced reachability line, the scheduler line with interval and
  limit, exact per-status counts, and the output format/quality/metadata line

#### Scenario: Health surfaces an unreachable server as the named code
- **WHEN** staff runs `@art health` while the server is unreachable
- **THEN** the server line reads unreachable with the named probe error code and the remaining
  sections still print

#### Scenario: Health is read-only
- **WHEN** `@art health` runs against a store with pending and failed records
- **THEN** every record's status, attempt count, and output identity are unchanged afterwards

#### Scenario: Health leaks nothing sensitive
- **WHEN** Basic auth is configured and staff runs `@art health`
- **THEN** no credential value, URL userinfo, or absolute path appears in the output

#### Scenario: Non-staff cannot run health
- **WHEN** a player without staff access runs `@art health`
- **THEN** the command is denied and no probe request is sent
