# art-asset-lifecycle Specification

## Purpose
Defines world/art/service.py as the sole writer of art asset and queue records and the lifecycle paths — startup sync and recovery, player creation and activation, validated named-NPC spawn, and room entry — that schedule portrait and scene asset ensures. Guarantees queue failures never roll back gameplay, canonical-age validation runs on every lifecycle path, and rejected prompt content never reaches the presenter or browser.

## Requirements

### Requirement: world/art/service.py is the sole writer of asset and queue records
`world/art/service.py` SHALL own every write to asset/queue records. No presenter module, no worker
module, no browser plugin, and no module under `world/ai/` SHALL create or mutate an asset/queue
record. The `world/art/` package SHALL carry no `world.ai`, `ollama`, or `llm_client` fragment, so the
repository deterministic-path contract test passes with no edit.

#### Scenario: The art package stays inside the deterministic-path ban
- **WHEN** the repository-wide deterministic-path contract scans `world/art/`
- **THEN** no production module under it carries a `world.ai`, `ollama`, or `llm_client` fragment, and
  no contract test requires an edit

#### Scenario: Presenters and workers hold no write surface
- **WHEN** the presenter and worker modules are inspected for a record-writing API
- **THEN** neither exposes a create/update/delete surface for asset records, and only `service.py` (or
  service-owned queue helpers) writes them

### Requirement: Startup recovery rescans explicit unique portrait policies
`art_sync_all()` SHALL also scan living characters that carry an explicit `{"mode": "named",
"stable_key": ...}` portrait policy and ensure each subject, recovering an enqueue that failed after an
earlier gameplay commit. A subject whose canonical ages fail the age check SHALL be skipped with a named
diagnostic and never retried by a later recovery pass for the same policy.

#### Scenario: A named policy with an empty gallery is recovered at startup
- **WHEN** a character has an explicit named portrait policy, an empty gallery, and no in-flight job after a restart
- **THEN** exactly one gallery generation is requested and no gameplay is rolled back

#### Scenario: A subject that already has a card is not regenerated
- **WHEN** recovery runs for a character whose gallery already holds a card, or whose generation is already in flight
- **THEN** nothing is requested and the gallery is unchanged

#### Scenario: An ineligible recovered subject is skipped deterministically
- **WHEN** a character with an explicit named policy fails the canonical-age check during recovery
- **THEN** no record is created, a named diagnostic is logged, and the same policy is not retried by a
  later recovery pass without re-running the gate

#### Scenario: The gallery satisfies recovery
- **WHEN** recovery evaluates a subject whose gallery already holds at least one card, or whose
  gallery generation is already in flight
- **THEN** the subject is left alone — the gallery satisfies the recovery

#### Scenario: A recovery request is one unbound auto-generated card
- **WHEN** recovery proceeds for a subject, which happens only for an empty gallery with no
  in-flight job
- **THEN** the requested image is one unbound auto-generated card, never a classic asset record

### Requirement: Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit
The player-creation activation path (after `world.rules.character_creation.activate_player_character`
succeeds) and the validated import path (`world/imports/loader.py`, inside the all-or-nothing batch)
SHALL establish the explicit named `portrait_policy` and SHALL schedule the portrait ensure through
`transaction.on_commit`, so the schedule fires only after the owning transaction commits. A rolled-back
or rejected creation/import SHALL emit no post-commit job.

#### Scenario: A committed creation schedules exactly one portrait ensure
- **WHEN** player creation commits successfully
- **THEN** the character carries an explicit named policy with a stable key and exactly one
  post-commit portrait ensure is scheduled

#### Scenario: A rolled-back creation emits no job
- **WHEN** a creation attempt fails and its transaction rolls back
- **THEN** no portrait policy is persisted and no post-commit portrait job is emitted

#### Scenario: A validated import schedules per eligible record
- **WHEN** an all-or-nothing import batch commits with validated named records carrying canonical ages
- **THEN** each imported named NPC carries an explicit named policy and one post-commit ensure is
  scheduled per record

#### Scenario: A rejected import batch emits no job
- **WHEN** an import batch fails validation and is rejected as a whole
- **THEN** no imported character carries a portrait policy and no post-commit job is emitted

### Requirement: Every player-activation path finalizes the portrait lifecycle
The system SHALL run identical portrait finalization — assigning the named `portrait_policy` and scheduling a post-commit portrait ensure — on every successful player activation path, Telnet and Web alike.

#### Scenario: Web activation assigns the portrait policy
- **WHEN** a character is activated through the Web creation flow
- **THEN** the character has a named `portrait_policy` with stable key `str(pk)` and exactly one portrait ensure is scheduled

#### Scenario: Telnet and Web activation produce identical portrait state
- **WHEN** a character is activated through Telnet and another through the Web flow
- **THEN** both characters carry the same policy shape and both have portrait jobs queued

#### Scenario: Rolled-back activation leaves no portrait state
- **WHEN** the activation transaction fails after the policy would have been assigned
- **THEN** no `portrait_policy` and no portrait job remain on the character

### Requirement: Validated named-NPC spawn schedules its portrait ensure after the spawn transaction commits
The SceneBuilder spawn path SHALL schedule the portrait ensure for a spawned occupant that carries an
explicit named portrait policy, through `transaction.on_commit`, so the schedule runs only after the
materialization transaction commits and an art failure can never roll back a materialized scene. A
spawned occupant with no policy (today's role-based scene NPCs and monsters) SHALL schedule nothing.

#### Scenario: A generic occupant schedules nothing
- **WHEN** a role-based scene NPC or monster is materialized
- **THEN** it carries no portrait policy and no post-commit portrait job is scheduled

#### Scenario: A named-policy occupant schedules after commit only
- **WHEN** a spawned occupant carries an explicit named portrait policy and the materialization
  commits
- **THEN** exactly one post-commit portrait ensure is scheduled for that occupant's subject

#### Scenario: A rolled-back materialization emits no job
- **WHEN** a materialization fails and its outer transaction rolls back
- **THEN** the on-commit callback never fires and no portrait job is emitted

### Requirement: Successful room entry ensures the scene asset for a validated archetype
On successful entry of a room whose class carries `SceneArchetypeMixin`, the art lifecycle SHALL call
`ensure_scene_asset()` for the room's validated `scene_archetype`, covering dynamic registry content
added after startup. A room with a `None` or unresolvable archetype SHALL be a side-effect-free no-op.

#### Scenario: Entering a scene-bearing room ensures its asset
- **WHEN** a player enters a grid or instance room whose `scene_archetype` resolves in the registry
- **THEN** the scene subject's gallery is ensured through the shared automatic-generation guard: one
  gallery request only when the subject has no card, no in-flight job, and either no gallery record
  or a record carrying a recorded error, nothing otherwise, and no classic record is created

#### Scenario: A room without a resolvable archetype is a no-op
- **WHEN** a player enters a room with a `None` or unresolvable `scene_archetype`
- **THEN** no record or job is created and no error propagates to the player's move

### Requirement: Queue failure never rolls back gameplay
Any art failure in a lifecycle seam — startup sync, recovery, creation, import, spawn, or room entry —
SHALL log a bounded diagnostic and SHALL NOT roll back or otherwise alter the gameplay transaction it
accompanies. The asset simply remains `missing`/`failed` for the next idempotent ensure. Every
`transaction.on_commit` art callback SHALL be an exception-safe wrapper.

#### Scenario: An art failure during creation leaves the creation committed
- **WHEN** the post-commit portrait ensure fails while player creation already committed
- **THEN** the character remains fully created with all gameplay state intact, the creation is reported
  as success, and a bounded diagnostic is logged

#### Scenario: An art failure during import does not surface as an import error
- **WHEN** the post-commit art callback raises after an all-or-nothing import batch committed
- **THEN** the import is still reported as committed, the imported characters are unchanged, and only a
  bounded diagnostic is logged

#### Scenario: An art failure during movement leaves the move committed
- **WHEN** `ensure_scene_asset()` fails during room entry
- **THEN** the player's move completes normally and only a bounded diagnostic is logged

#### Scenario: An art exception inside an on-commit wrapper is swallowed
- **WHEN** an art exception is raised inside a `transaction.on_commit` art callback
- **THEN** it is caught and logged, never propagated to the owning creation/import workflow, so a
  committed gameplay transaction is always reported as success even when the art hook fails

### Requirement: Portrait-character enqueue validates canonical age attributes immediately before enqueue
`world/art/subjects.py` SHALL expose `character_ages(entity)` that reads `age` and `apparent_age`
from the character's canonical attributes and raises a named `ArtSubjectError` diagnostic identifying
the failing field when either value is missing or non-integer. `world/art/service.py` SHALL run this
check for every `portrait:character` subject immediately before any queue record is written.

#### Scenario: A valid integer record reaches the worker fixture
- **WHEN** a character with `age = 22` and `apparent_age = 22` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes and a fixture worker receives a job whose description contains the
  character's canonical identity

#### Scenario: A zero age is a valid canonical value
- **WHEN** a character with `age = 0` and `apparent_age = 0` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes, since any integer is a valid canonical age

#### Scenario: A missing age rejects with a named diagnostic
- **WHEN** a character's `age` or `apparent_age` attribute is absent
- **THEN** a named `ArtSubjectError` is raised with the failing field identified, no queue record is
  created, no prompt text is produced, and the worker fixture is never invoked

#### Scenario: A non-integer age rejects with a named diagnostic
- **WHEN** a character's `age` or `apparent_age` attribute is a string or otherwise non-integer
- **THEN** a named `ArtSubjectError` is raised with the failing field identified, no queue record is
  created, no prompt text is produced, and the worker fixture is never invoked

#### Scenario: The enqueue check supplements the schema validation
- **WHEN** the enqueue-time age check runs for a `portrait:character` subject
- **THEN** it runs in addition to the schema/creation validation that already checked the same
  fields

#### Scenario: A rejection is logged for staff review
- **WHEN** the enqueue-time age check rejects a subject
- **THEN** the rejection is logged with the named diagnostic for staff review

### Requirement: The age check runs on every lifecycle path and rejects deterministically without a persisted marker
`world/art/service.py` SHALL apply the canonical-age check at schedule time and again before the queue
write for every lifecycle path that can produce a `portrait:character` subject — player creation,
validated import, named-NPC spawn, staff retry, staff requeue, and startup recovery. Because the check
is a pure function of the canonical age attributes, every attempt against the same bad data SHALL
reject with the same named diagnostic.

#### Scenario: An import with malformed ages never enqueues
- **WHEN** an import path is forced to schedule a portrait subject for a character whose canonical age
  data is missing or non-integer
- **THEN** the check rejects before any record write and the worker fixture receives nothing

#### Scenario: An ineligible recovered subject is skipped deterministically
- **WHEN** a character with an explicit named policy fails the canonical-age check during recovery
- **THEN** no record is created, a named diagnostic is logged, and a later recovery pass for the same
  bad data rejects identically without creating a record

#### Scenario: A staff retry or requeue re-runs the check
- **WHEN** a staff retry or requeue targets a character portrait whose owning entity carries missing or
  non-integer canonical ages
- **THEN** the check rejects with the named diagnostic, the record is unchanged, and no worker call
  occurs

#### Scenario: No persisted rejection marker is required
- **WHEN** a subject is rejected by the canonical-age check
- **THEN** no separate persisted rejection marker is required, because the check is a pure function of
  the canonical age attributes

#### Scenario: Rejected subjects are not retried periodically
- **WHEN** a subject keeps failing the canonical-age check
- **THEN** no attempt is retried periodically — attempts occur only on lifecycle events

#### Scenario: Corrected age data restores eligibility
- **WHEN** a subject that failed the check has its canonical age data corrected
- **THEN** it is eligible again and the next lifecycle attempt passes

### Requirement: Rejected prompt content never reaches the presenter or browser
The presenter-facing surface SHALL never contain a rejected prompt or an ineligible character's
identity. A `portrait:character` subject that failed the canonical-age check SHALL resolve only to the
unavailable placeholder with its explanatory label and alternative text.

#### Scenario: The presenter surface is free of rejected content
- **WHEN** an age-check-rejected character is queried through the read-only presenter primitives
- **THEN** the result is the unavailable placeholder with a label and safe alternative text, and no
  prompt text or ineligible identity appears in the payload

### Requirement: Startup converts classic scene outputs into scene gallery cards
Before the gallery orphan prune, startup SHALL convert every settled classic scene record: a `done` record whose output is presentable becomes the archetype's scene gallery card when the gallery holds none; then the record and its classic output files SHALL be deleted. Unsettled records SHALL be left for a later startup. The step SHALL be idempotent, bounded per record, and leave no orphan file or record.

#### Scenario: A done classic scene becomes one card
- **WHEN** synthetic archetype `t_arch` has a `done` classic record with a presentable output and an empty scene gallery
- **THEN** after startup its gallery holds exactly one default card whose file holds the same bytes, and neither the classic record nor the classic output file remains

#### Scenario: An existing card wins
- **WHEN** `t_arch` already holds a scene gallery card and also a `done` classic record
- **THEN** the card is unchanged, and the classic record and its output files are deleted

#### Scenario: Failed and missing records are dropped
- **WHEN** a classic scene record is `failed`, `missing`, or `done` without a presentable output
- **THEN** it and any of its output files are deleted and no card is created

#### Scenario: An unsettled record waits
- **WHEN** a classic scene record is `pending` or `in_progress`
- **THEN** it is left unchanged

#### Scenario: Running twice changes nothing more
- **WHEN** the conversion runs a second time
- **THEN** it creates, deletes and moves nothing

#### Scenario: One bad record never aborts startup
- **WHEN** converting one record raises
- **THEN** a bounded diagnostic is logged, the other records are converted, and startup continues

### Requirement: Startup synchronization requests gallery art for every registered scene and species
`world/art/service.py::art_sync_all()` SHALL be called from
`server/conf/at_server_startstop.py::at_server_start` and SHALL cover every entry of
`SCENE_ARCHETYPE_REGISTRY` and every registered visual species (species-keyed monster subjects),
routing each subject by whether its kind declares a gallery.

#### Scenario: Every registered subject has a record after startup sync
- **WHEN** startup art synchronization runs against a fresh database
- **THEN** each scene archetype and each visual species with no card, in-flight job or satisfying official default receives one gallery request, and no classic scene or monster record is created

#### Scenario: A seed-carded tier survives the ordered startup unchanged
- **WHEN** the startup steps run in catalog order (prune, then seed synchronization, then this
  synchronization) with a seed image present for a registered visual species, and the queue is later drained
- **THEN** no gallery generation is requested for that species and its seed card and stored file are never replaced

#### Scenario: Sync leaves existing pending, in-progress, and done records untouched
- **WHEN** `art_sync_all()` runs after records were already created, claimed, or completed
- **THEN** the existing `pending`, `in_progress`, and `done` records are not reset, not duplicated, and
  not overwritten

#### Scenario: A pre-existing classic monster record is left alone
- **WHEN** startup synchronization encounters a valid classic species record or a retired tier record
- **THEN** valid species output remains read-only and resolvable; retired tier records are never applied, served, requeued or converted into species records

#### Scenario: Duplicate records for one subject are consolidated
- **WHEN** startup sync finds more than one record for the same subject key
- **THEN** exactly one record remains (the most advanced) and the rest are removed

#### Scenario: A monster gallery request failure never aborts startup
- **WHEN** a monster visual species's gallery request raises during startup synchronization
- **THEN** a bounded diagnostic is logged, the remaining subjects still synchronize, and startup completes

#### Scenario: A carded scene requests nothing
- **WHEN** startup synchronization meets a scene archetype whose gallery already holds a card or an in-flight job
- **THEN** no gallery request is made for it and the sync is idempotent

#### Scenario: A scene emptied by deletion stays on its bundled image
- **WHEN** startup synchronization or a room entry meets a scene archetype whose gallery record exists with no card because its card was deleted
- **THEN** no gallery request is made, so the archetype keeps resolving its bundled image until a player requests a new one

#### Scenario: A failed first generation is retried
- **WHEN** an archetype's first scene generation failed, leaving a gallery record with no card and a recorded error, and the player enters one of its rooms
- **THEN** one new gallery request is made

#### Scenario: Records are created only under the queue lock
- **WHEN** the sync needs to create a record for a subject that has none
- **THEN** the record is created only through an atomic find-or-create under the queue lock, so
  per-subject uniqueness holds

#### Scenario: A gallery-kind subject routes through the gallery request
- **WHEN** `art_sync_all()` ensures a subject whose kind declares a gallery — the scene kind and the species-keyed monster kind
- **THEN** it routes through the gallery generation request under the shared automatic-generation
  guard, and startup does not create a classic asset record for it

#### Scenario: Pre-existing classic monster records require no migration
- **WHEN** startup encounters old tier-keyed classic monster records
- **THEN** they remain unreachable under current membership validation; no compatibility path or migration makes them usable

#### Scenario: Any startup synchronization failure stays bounded
- **WHEN** any failure occurs during startup synchronization
- **THEN** it stays bounded and never aborts startup

#### Scenario: Seed synchronization and the orphan prune run first
- **WHEN** the startup steps run in order
- **THEN** the gallery orphan prune and the bulk seed synchronization run BEFORE this
  synchronization, so a seed card already occupies a subject's gallery — and the prune has already
  swept — before any automatic gallery request is enqueued; an operator seed card is therefore never
  displaced by a startup-time generation
