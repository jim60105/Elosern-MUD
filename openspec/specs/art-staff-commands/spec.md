# art-staff-commands Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
## Requirements
### Requirement: @art status lists and filters records without leaking sensitive data
`commands/art.py::CmdArtStatus` (`@art status [scene|portrait]`) SHALL list asset records filtered by
subject kind, showing subject key, status, aspect ratio, attempt count, bounded error code, and —
only when the record carries one — the persisted generation seed. Output
SHALL NOT include persona text, prompt content, absolute filesystem paths, or the store root.

The command SHALL additionally report gallery STATE in its own clearly separated section, honoring the
same kind filter: one line per `GalleryRecord` carrying its full subject key, the number of valid
cards, whether a default is set, and — only when one is recorded — the bounded generation error code
with the age of that error. Per-image gallery JOB records SHALL remain invisible in every section, as
they are today: this section reports what a subject's gallery holds, never queue rows. Cross-record
gallery state SHALL be read exclusively through the gallery module's read-only accessors, never by
querying the record class from the command. The gallery section SHALL obey the same non-leakage rule
as the rest of the output: no prompt text, no persona text, no stored identity, and no absolute path.

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

#### Scenario: A failed gallery generation is visible to staff
- **WHEN** a subject's gallery carries a recorded generation error and staff runs `@art status`
- **THEN** the gallery section names that subject with its bounded error code, and no prompt text or stored identity appears

#### Scenario: Gallery job records stay invisible
- **WHEN** a gallery job is pending for a subject and staff runs `@art status`
- **THEN** no job row appears in any section and the subject's gallery line reports its cards only

#### Scenario: A subject with a healthy gallery reports no error
- **WHEN** a subject holds cards and carries no recorded error and staff runs `@art status`
- **THEN** its gallery line shows the card count and default state with no error field

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
`commands/art.py::CmdArtRetry` (`@art retry`) SHALL re-enqueue every `failed` classic subject record to
`pending` under the queue lock and SHALL, in the same pass, re-drive every subject whose `GalleryRecord`
carries a recorded generation error through the gallery request seam. It SHALL report both counts.

A gallery re-drive SHALL go through the same validated request seam an automatic path uses, so every
precondition that seam enforces still applies and a subject that no longer qualifies is skipped with no
record change rather than failing the whole command. Because a character subject no longer owns a
classic asset record, `queue.failed_keys()` can no longer yield one; the command SHALL NOT carry a
classic-character re-enqueue branch, and the gallery arm SHALL be the only character retry path.

When the seam declines an erroring subject because its gallery is no longer empty — a seed card
arrived, or an operator kept an image — the recorded error SHALL be cleared rather than left standing.
The subject has art and its automatic guard will suppress every future request, so nothing else would
ever clear that code and it would otherwise remain permanently on the status surface. A subject
declined for any other reason SHALL keep its recorded error.

#### Scenario: Failed records are re-enqueued
- **WHEN** staff runs `@art retry` with failed classic (scene) records present
- **THEN** each failed record becomes `pending` and the command reports the re-enqueued count

#### Scenario: A failed gallery generation is retried without a restart
- **WHEN** a character subject's gallery carries a recorded generation error and staff runs `@art retry`
- **THEN** exactly one gallery generation is requested for that subject and the command reports it

#### Scenario: An ineligible erroring subject is skipped, not fatal
- **WHEN** a subject carrying a recorded gallery error no longer satisfies the request seam's preconditions
- **THEN** that subject is skipped with no record change, the remaining subjects are still retried, and the command reports the count it actually requested

#### Scenario: A moot error on a subject that now has art is cleared
- **WHEN** a subject carrying a recorded gallery error has since gained a card and staff runs `@art retry`
- **THEN** no generation is requested for it, its recorded error is cleared, and it no longer appears as erroring on the status surface

#### Scenario: A healthy gallery is left alone
- **WHEN** staff runs `@art retry` and every gallery record carries no error
- **THEN** no gallery generation is requested and the command reports zero gallery retries

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
`commands/art.py::CmdArtRequeue` (`@art requeue <full-subject-key>`) SHALL parse and validate exactly
one full subject key through the subject parser. An invalid key SHALL be rejected with a named error
and no record change. A key whose subject kind declares NO gallery — a scene key — SHALL reset the
classic record to `pending` under the queue lock, preserve the prior valid output, and SHALL be the
only way an ordinary-lifecycle pass can force regeneration of that record.

A key whose subject kind declares a gallery — character and generic monster alike — SHALL instead
issue exactly one gallery generation request for that subject through the shared request seam,
appending a new card on success. Requeue is the staff force path: it SHALL deliberately bypass the
automatic-generation idempotency guard, so a subject that already holds cards still gets one new
generation. For a kind whose declared card maximum the new card would exceed, the append SHALL respect
that maximum exactly as any other append does — for the monster kind, replacing its single card. For a
kind with no declared maximum, the existing cards SHALL be untouched. Neither path SHALL create a
classic asset record for a gallery-bearing subject.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:forest_path`
- **THEN** the scene record becomes `pending`, its prior valid output is preserved, and a regeneration
  is queued under the queue lock

#### Scenario: An invalid key is rejected with no record change
- **WHEN** staff runs `@art requeue` with a malformed or unknown full subject key
- **THEN** a named error is returned and no record is changed

#### Scenario: A character key requeue adds a gallery card
- **WHEN** staff runs `@art requeue portrait:character:<stable-key>` for a subject that already holds cards
- **THEN** one gallery generation is requested, no classic asset record is created, and the existing cards are untouched until the new card is appended

#### Scenario: A monster key requeue requests a gallery card honouring the cap
- **WHEN** staff runs `@art requeue portrait:monster:<tier>` for a tier that already holds its one card
- **THEN** one gallery generation is requested, no classic asset record is created, and the settled card replaces the existing one under the declared maximum

#### Scenario: A monster requeue never resets a classic record
- **WHEN** staff runs `@art requeue portrait:monster:<tier>` for a tier that still has a pre-existing classic asset record
- **THEN** a gallery generation is requested and that classic record's status is unchanged

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
one forced connectivity probe and prints five sections in fixed order: (1) server reachability —
`reachable` or `unreachable` with the named error code and that the check ran just now; (2) the
effective scheduler state (`ART_SCHEDULER_ENABLED` with interval seconds and limit); (3) exact
record counts by status (`pending`, `in_progress`, `failed`, `done`); (4) exact gallery counts —
gallery records, total valid cards, and subjects currently carrying a recorded generation error;
(5) the effective output policy (`ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`, and whether
generation-metadata preservation is on). The command SHALL mutate no record, queue entry, or setting,
and its output SHALL NOT contain credentials, URL userinfo, absolute paths, prompt text, or persona
text.

#### Scenario: Health shows a reachable server with full dashboard state
- **WHEN** staff runs `@art health` against a reachable server with the scheduler enabled and a
  mixed-status record store
- **THEN** the output shows the forced reachability line, the scheduler line with interval and
  limit, exact per-status counts, the gallery counts line, and the output format/quality/metadata line

#### Scenario: Health counts subjects carrying a gallery error
- **WHEN** two subjects carry recorded gallery errors and staff runs `@art health`
- **THEN** the gallery line reports exactly two erroring subjects alongside the record and card counts

#### Scenario: Health surfaces an unreachable server as the named code
- **WHEN** staff runs `@art health` while the server is unreachable
- **THEN** the server line reads unreachable with the named probe error code and the remaining
  sections still print

#### Scenario: Health is read-only
- **WHEN** `@art health` runs against a store with pending and failed records
- **THEN** every record's status, attempt count, and output identity are unchanged afterwards, and no gallery record, card, or recorded error is altered

#### Scenario: Health leaks nothing sensitive
- **WHEN** Basic auth is configured and staff runs `@art health`
- **THEN** no credential value, URL userinfo, or absolute path appears in the output

#### Scenario: Non-staff cannot run health
- **WHEN** a player without staff access runs `@art health`
- **THEN** the command is denied and no probe request is sent

