# art-staff-commands delta specification

## ADDED Requirements

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

## MODIFIED Requirements

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
