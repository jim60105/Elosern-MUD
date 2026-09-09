# art-asset-lifecycle Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
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

### Requirement: Startup synchronization idempotently ensures scene and generic-monster records
`world/art/service.py::art_sync_all()` SHALL be called from
`server/conf/at_server_startstop.py::at_server_start` and SHALL cover every entry of
`SCENE_ARCHETYPE_REGISTRY` and every entry of `MONSTER_TIER_REGISTRY` (generic monster subjects),
routing each subject by whether its kind declares a gallery.

A subject whose kind declares NO gallery — the scene kind — SHALL be ensured as a classic asset record
exactly as today: the sync SHALL be idempotent, an existing `pending`, `in_progress`, or `done` record
is untouched, a `missing` or `failed` record is made `pending`, records SHALL be created only through
an atomic find-or-create under the queue lock, and the sync SHALL consolidate any duplicate records
found for one subject (keeping the most-advanced record) so per-subject uniqueness holds.

A subject whose kind declares a gallery — the generic monster kind — SHALL instead route through the
gallery generation request under the shared automatic-generation guard, and startup SHALL NOT create a
classic asset record for it. Pre-existing classic monster records SHALL be left in place: they are not
deleted, not reset, and keep resolving through the display chain's classic step, so no migration is
required. Every failure SHALL stay bounded and SHALL never abort startup.

The startup step order SHALL run the gallery orphan prune and the bulk seed synchronization BEFORE
this synchronization, so a seed card already occupies a subject's gallery — and the prune has already
swept — before any automatic gallery request is enqueued; an operator seed card is therefore never
displaced by a startup-time generation.

#### Scenario: Every registered subject has a record after startup sync
- **WHEN** `art_sync_all()` runs against a fresh database
- **THEN** every `SCENE_ARCHETYPE_REGISTRY` key has exactly one classic asset record in `missing` or
  `pending` state, every `MONSTER_TIER_REGISTRY` key has one gallery generation requested, and no
  classic asset record is created for any monster tier

#### Scenario: A seed-carded tier survives the ordered startup unchanged
- **WHEN** the startup steps run in catalog order (prune, then seed synchronization, then this
  synchronization) with a seed image present for a monster tier, and the queue is later drained
- **THEN** no gallery generation is requested for that tier and its seed card and stored file are never replaced

#### Scenario: Sync leaves existing pending, in-progress, and done records untouched
- **WHEN** `art_sync_all()` runs after records were already created, claimed, or completed
- **THEN** the existing `pending`, `in_progress`, and `done` records are not reset, not duplicated, and
  not overwritten

#### Scenario: A pre-existing classic monster record is left alone
- **WHEN** `art_sync_all()` runs against a store that already holds a `done` classic monster record
- **THEN** that record is not deleted, not reset, and still resolves through the display chain's classic step

#### Scenario: Duplicate records for one subject are consolidated
- **WHEN** startup sync finds more than one record for the same subject key
- **THEN** exactly one record remains (the most advanced) and the rest are removed

#### Scenario: A monster gallery request failure never aborts startup
- **WHEN** a monster tier's gallery request raises during startup synchronization
- **THEN** a bounded diagnostic is logged, the remaining subjects still synchronize, and startup completes

### Requirement: Startup recovery rescans explicit unique portrait policies
`art_sync_all()` SHALL also scan living characters that carry an explicit `{"mode": "named",
"stable_key": ...}` portrait policy and ensure each subject, recovering an enqueue that failed after an
earlier gameplay commit. A subject whose canonical ages fail the age check SHALL be skipped with a named
diagnostic and never retried by a later recovery pass for the same policy.

The recovery SHALL be satisfied by the subject's GALLERY: a subject whose gallery already holds at
least one card, or whose gallery generation is already in flight, SHALL be left alone, and only a
subject with an empty gallery and no in-flight job SHALL be requested. The requested image SHALL be
one unbound auto-generated card, never a classic asset record.

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
- **THEN** the scene subject's asset record is ensured (created if missing, untouched if pending or
  done)

#### Scenario: A room without a resolvable archetype is a no-op
- **WHEN** a player enters a room with a `None` or unresolvable `scene_archetype`
- **THEN** no record is created and no error propagates to the player's move

### Requirement: Queue failure never rolls back gameplay
Any art failure in a lifecycle seam — startup sync, recovery, creation, import, spawn, or room entry —
SHALL log a bounded diagnostic and SHALL NOT roll back or otherwise alter the gameplay transaction it
accompanies. The asset simply remains `missing`/`failed` for the next idempotent ensure. Every
`transaction.on_commit` art callback SHALL be an exception-safe wrapper: an art exception raised
inside it SHALL be caught and logged, never propagated to the owning creation/import workflow, so a
committed gameplay transaction is always reported as success even when the art hook fails.

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

### Requirement: Portrait-character enqueue validates canonical age attributes immediately before enqueue
`world/art/subjects.py` SHALL expose `character_ages(entity)` that reads `age` and `apparent_age`
from the character's canonical attributes and raises a named `ArtSubjectError` diagnostic identifying
the failing field when either value is missing or non-integer. `world/art/service.py` SHALL run this
check for every `portrait:character` subject immediately before any queue record is written, in
addition to the schema/creation validation that already checked the same fields. A rejection SHALL
produce no queue record and no prompt text, SHALL never reach a worker fixture, and SHALL be logged
with the named diagnostic for staff review.

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

### Requirement: The age check runs on every lifecycle path and rejects deterministically without a persisted marker
`world/art/service.py` SHALL apply the canonical-age check at schedule time and again before the queue
write for every lifecycle path that can produce a `portrait:character` subject — player creation,
validated import, named-NPC spawn, staff retry, staff requeue, and startup recovery. Because the check
is a pure function of the canonical age attributes, every attempt against the same bad data SHALL
reject with the same named diagnostic; no separate persisted rejection marker is required, and no
attempt SHALL be retried periodically (attempts occur only on lifecycle events). A subject that failed
the check SHALL be eligible again once its canonical age data is corrected, at which point the next
lifecycle attempt passes.

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

### Requirement: Rejected prompt content never reaches the presenter or browser
The presenter-facing surface SHALL never contain a rejected prompt or an ineligible character's
identity. A `portrait:character` subject that failed the canonical-age check SHALL resolve only to the
unavailable placeholder with its explanatory label and alternative text.

#### Scenario: The presenter surface is free of rejected content
- **WHEN** an age-check-rejected character is queried through the read-only presenter primitives
- **THEN** the result is the unavailable placeholder with a label and safe alternative text, and no
  prompt text or ineligible identity appears in the payload

