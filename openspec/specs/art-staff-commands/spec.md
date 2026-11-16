# art-staff-commands Specification

## Purpose
Defines the staff-only @art command surface — status listing with filters and gallery state, run to drain the queue, retry and requeue for regeneration, options, and health reporting — each bounded so output never leaks persona text, prompt content, absolute paths, or the store root. Guarantees players have no access to any art control.

## Requirements

### Requirement: @art run drains the shared queue now with an optional limit
`commands/art.py::CmdArtRun` (`@art run [--limit N]`) SHALL drain pending records through the shared
worker boundary asynchronously, never blocking play, honoring the queue lock, and SHALL report how
many jobs were dispatched (or the named error when the worker cannot start).

#### Scenario: A bounded drain dispatches pending jobs
- **WHEN** staff runs `@art run --limit 5` with pending records present
- **THEN** at most five pending records are dispatched through the worker and the command reports the
  count dispatched

### Requirement: Players have no access to any art control
No `@art` subcommand SHALL be available to ordinary players. Player-triggered generation SHALL exist
only through the gallery management actions, for subjects admitted to the acting player.

#### Scenario: All subcommands require staff
- **WHEN** every `@art` subcommand's access is exercised with a non-staff caller
- **THEN** each is denied and no queue, store, or worker operation runs

### Requirement: @art options lists the live server's selectable option names
`commands/art.py` SHALL provide `@art options <models|samplers|schedulers|styles|modules>`
restricted to `Developer`, which performs one bounded read-only enumeration of the configured
sd-webui server (no queue, record, or setting mutation) and prints the exact selectable names,
one per line, with a header naming the option kind and total count.

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

#### Scenario: A bad argument is rejected with the usage line and no request
- **WHEN** the argument is missing, unknown, or multi-word
- **THEN** it SHALL be rejected with the usage line and no request sent

#### Scenario: An enumeration failure prints only the named error code
- **WHEN** any enumeration failure occurs
- **THEN** the command SHALL print the named error code and no partial list

#### Scenario: Display names are bounded per line
- **WHEN** option display names are printed
- **THEN** they SHALL be bounded to 256 code points per line

#### Scenario: The output names no credentials and at most the server host
- **WHEN** the options output renders
- **THEN** it SHALL NOT include the configured credentials or any `Authorization` material, and
  SHALL name at most the server host (never a URL containing userinfo)

### Requirement: Staff status reports gallery holdings without sensitive data
Staff status SHALL list gallery holdings/default/error state with the existing scene/portrait filter. Per-image jobs SHALL remain absent from status rows. No completed subject-record section or legacy seed row SHALL remain. Output SHALL exclude prompts, persona, stored identities and absolute paths.

#### Scenario: Gallery state is filtered and private
- **WHEN** staff requests status with scene or portrait filters
- **THEN** only matching gallery holdings/default/errors appear; pending job rows and sensitive data do not

#### Scenario: Staff permission remains enforced
- **WHEN** an ordinary player invokes status
- **THEN** access is denied without queue or gallery operations

### Requirement: Staff retry re-drives recorded gallery failures
Staff retry SHALL re-drive subjects with recorded gallery errors through the existing validated automatic gallery seam, report the count requested and preserve per-subject failure isolation. Existing cards SHALL suppress requests and clear moot errors; other declined requests SHALL retain errors. No classic count or record reset SHALL remain.

#### Scenario: Gallery errors retry without restart
- **WHEN** eligible subjects have recorded gallery errors and no cards, in-flight jobs or satisfying official defaults
- **THEN** each gets one new image request and the command reports the requested count

#### Scenario: Moot errors clear
- **WHEN** an erroring subject has gained a valid card
- **THEN** no request occurs and its error clears

#### Scenario: Other declines preserve errors
- **WHEN** an erroring subject is official-satisfied, already in flight or ineligible
- **THEN** its error stays and no job is added; other eligible subjects continue

### Requirement: Staff requeue forces one validated gallery request
Staff requeue SHALL parse one full typed subject key and request one gallery image, bypassing automatic satisfaction by cards or official defaults while retaining capability preconditions. Invalid or gallery-less subjects SHALL reject without writes. Capped subjects SHALL replace on successful settlement; uncapped subjects SHALL retain existing cards.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:<archetype>` for a registered synthetic archetype that holds one card
- **THEN** one gallery generation is requested, no fixed-output record is created, and the existing
  card stays until the new card replaces it under the declared maximum

#### Scenario: An invalid key is rejected with no record change
- **WHEN** staff runs `@art requeue` with a malformed or unknown full subject key
- **THEN** a named error is returned and no record is changed

#### Scenario: A character key requeue adds a gallery card
- **WHEN** staff runs `@art requeue portrait:character:<stable-key>` for a subject that already holds cards
- **THEN** one gallery generation is requested, no fixed-output record is created, and the existing cards are untouched until the new card is appended

#### Scenario: A monster key requeue requests a gallery card honouring the cap
- **WHEN** staff runs `@art requeue portrait:monster:<visual-key>` for a visual species that already holds its one card
- **THEN** one gallery generation is requested, no fixed-output record is created, and the settled card replaces the existing one under the declared maximum

#### Scenario: A gallery-bearing key issues one request through the shared seam
- **WHEN** the requeue key's subject kind declares a gallery — character and species-keyed monster alike
- **THEN** the command SHALL instead issue exactly one gallery generation request for that subject
  through the shared request seam, appending a new card on success

#### Scenario: Requeue deliberately bypasses the idempotency guard
- **WHEN** requeue targets a subject that already holds cards
- **THEN** because requeue is the staff force path, it SHALL deliberately bypass the
  automatic-generation idempotency guard, so the subject still gets one new generation

#### Scenario: The append respects the declared card maximum
- **WHEN** the new card would exceed the kind's declared card maximum
- **THEN** the append SHALL respect that maximum exactly as any other append does — for the monster
  kind, replacing its single card

#### Scenario: A kind with no declared maximum keeps its existing cards
- **WHEN** the kind declares no card maximum
- **THEN** the existing cards SHALL be untouched

#### Scenario: Every force request creates a per-image job
- **WHEN** either requeue path runs for a gallery-bearing subject
- **THEN** only a per-image gallery job SHALL be created for that subject

#### Scenario: Retired monster tiers never requeue
- **WHEN** staff supplies any threat-tier key as a monster requeue subject
- **THEN** a named invalid-subject error is returned with no generation, record reset or conversion

### Requirement: Staff health separates live jobs from gallery outcome state
Developer health SHALL perform one forced connectivity probe and report reachability, scheduler policy, live gallery-job pending/in_progress counts, gallery holdings/card/error counts, and output policy in that order. Deleted terminal jobs SHALL NOT be represented as persistent done/failed queue rows. It SHALL remain read-only and leak no credentials, paths or prompts.

#### Scenario: Live counts reflect actual job lifetime
- **WHEN** one job is pending, another claimed and a previous failed job has been removed
- **THEN** health reports one pending and one in_progress job, the recorded gallery error separately, and no terminal queue history

#### Scenario: Probe failure does not hide other sections
- **WHEN** the forced probe fails
- **THEN** the bounded error appears with scheduler, gallery and output sections; no state changes
