# art-staff-commands delta specification

## ADDED Requirements

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
