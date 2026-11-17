# art-gallery-autogen Specification

## Purpose

Define how every automatic character-portrait path — player creation, validated
import, named-NPC spawn, startup recovery, and staff retry/requeue — routes
through the gallery generation seam: exactly one unbound card built from the
subject's standard deterministic description with the shared default face
rectangle and no classic fixed-identity record, guarded for idempotency
against the subject's gallery, with the existing age-check, post-commit, and
failure-isolation guarantees intact. Player creation carries an explicit skip
flag that establishes the named policy without requesting anything.

## Requirements

### Requirement: Automatic generation is idempotent against the subject's gallery
An automatic path SHALL request a generation only when the subject's gallery holds no card AND no
gallery job for that subject is in flight AND no official default resolves for it. A subject that
already holds any card SHALL be left alone. The guard SHALL be the same one for every
gallery-bearing kind.

#### Scenario: Repeated recovery appends nothing
- **WHEN** startup recovery runs on consecutive restarts for a subject that already holds one card
- **THEN** no additional generation is requested and the gallery still holds one card

#### Scenario: Repeated startup synchronization never replaces a monster card
- **WHEN** startup synchronization runs on consecutive restarts for a monster visual species that already holds its one card
- **THEN** no generation is requested, the existing card is not replaced, and its stored file is untouched

#### Scenario: A seed-synced subject is not auto-generated
- **WHEN** an automatic path runs for a subject whose only card came from seed synchronization
- **THEN** no generation is requested

#### Scenario: An in-flight job suppresses a second request
- **WHEN** an automatic path runs for a subject whose gallery job is already pending or in progress
- **THEN** no second job is enqueued

#### Scenario: Satisfying official artwork suppresses the initial automatic generation
- **WHEN** a preset-born character activates with an empty gallery while its preset content reference resolves a valid official default
- **THEN** no gallery generation is enqueued, the character still carries its named portrait policy, and it presents the official default

#### Scenario: An ineligible or unsatisfied reference does not suppress
- **WHEN** an automatic path runs for an entity with no content reference, or one the snapshot does not hold
- **THEN** the existing automatic request proceeds exactly as today

#### Scenario: Manual generation remains available after suppression
- **WHEN** an entity whose automatic generation was official-suppressed is later requested through the manual gallery generation seam
- **THEN** the request is served through the existing seam and settles a runtime card that then outranks the official default

#### Scenario: Any existing card kind counts as held
- **WHEN** the idempotency guard finds the subject's only card
- **THEN** a generated, seed-synced, or player-kept card all count, and the subject is left alone

#### Scenario: The guard holds across restarts
- **WHEN** startup recovery and startup synchronization repeat across restarts
- **THEN** they never stack duplicate cards

#### Scenario: The guard holds across quests
- **WHEN** several scenes share one `stable_key`
- **THEN** they yield exactly one auto-generated card

#### Scenario: One rule protects every gallery-bearing kind
- **WHEN** the guard is applied per kind
- **THEN** a monster visual species is protected by exactly the rule a character subject is — which is also what
  keeps a capped kind from replacing its one card on every restart

#### Scenario: A suppressed request leaves nothing and is not revived later
- **WHEN** an automatic request is suppressed
- **THEN** it leaves no record and enqueues nothing; the entity presents the official default through
  the presentation chain, and updating the official directory later does not retroactively enqueue the
  suppressed subject

#### Scenario: Species startup suppression needs no spawned monster
- **WHEN** a registered visual species has a valid official default and no live individual exists
- **THEN** startup queues no automatic card for that species, and later individuals present that species official artwork

#### Scenario: Registry subjects suppress without an entity
- **WHEN** automatic synchronization visits a registered scene or monster subject with no entity and a resolvable official catalog default
- **THEN** no job, gallery record, default card or prompt is created; manual generation remains available

#### Scenario: Bundled terminals are not catalog defaults
- **WHEN** a scene has only its bundled terminal and has never requested or deleted a card
- **THEN** normal automatic generation remains eligible; bundled terminal availability alone does not satisfy the official-catalog guard

### Requirement: Player creation may skip the automatic portrait
`world/rules/character_creation.py::finalize_player_portrait` SHALL accept an explicit skip flag,
defaulting to generating. It SHALL establish the explicit named `portrait_policy` on every path,
including the skipped one. A skipped creation
SHALL enqueue nothing and SHALL leave the character with an empty gallery. The flag SHALL
be read inside the activation transaction like
the rest of the finalization, so a rollback leaves no portrait state either way.

#### Scenario: A skipped creation starts with an empty gallery
- **WHEN** a character is activated with the skip flag set
- **THEN** it carries the named portrait policy, its gallery is empty, no job is enqueued, and it resolves through the standard chain's terminal fallback seam rather than owning any portrait state of its own

#### Scenario: The default path still generates
- **WHEN** a character is activated without the skip flag, without a satisfying official default and without an existing card or in-flight job
- **THEN** exactly one post-commit gallery generation is scheduled

#### Scenario: A rolled-back skipped activation leaves nothing
- **WHEN** an activation with the skip flag set rolls back
- **THEN** no portrait policy and no gallery state remain on the character

#### Scenario: The empty gallery resolves through the terminal fallback seam
- **WHEN** a skipped character's empty gallery is presented
- **THEN** it resolves through the standard chain's terminal fallback seam (inert until the
  gallery-fallback capability fills it — today the honest outcome is the truthful placeholder, owned
  by ``gallery-builtin-fallbacks``)
- **AND** establishing the policy on every path keeps the character eligible for a later request

### Requirement: Gallery lifecycle writes stay inside the deterministic art owner
`world/art/service.py` SHALL own every write to gallery/queue records. No presenter module, no worker
module, no browser plugin, and no module under `world/ai/` SHALL create or mutate an asset/queue
record. The `world/art/` package SHALL carry no `world.ai`, `ollama`, or `llm_client` fragment, so the
repository deterministic-path contract test passes with no edit.

#### Scenario: The art package stays inside the deterministic-path ban
- **WHEN** the repository-wide deterministic-path contract scans `world/art/`
- **THEN** no production module under it carries a `world.ai`, `ollama`, or `llm_client` fragment, and
  no contract test requires an edit

#### Scenario: Presenters and workers hold no write surface
- **WHEN** the presenter and worker modules are inspected for a record-writing API
- **THEN** neither exposes a create/update/delete surface for gallery job records, and only `service.py` (or
  service-owned queue helpers) writes them

### Requirement: Startup recovery rescans explicit unique portrait policies
Startup SHALL recover activated characters’ explicit named portrait policies through the shared automatic gallery guard, including official-default suppression. Invalid canonical ages SHALL reject deterministically with a bounded diagnostic and no persisted rejection marker. Repeated attempts on unchanged invalid data SHALL reject identically.

#### Scenario: A named policy with an empty gallery is recovered at startup
- **WHEN** an eligible character has an explicit named portrait policy, an empty gallery, no in-flight job and no satisfying official default after a restart
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
  in-flight job and no satisfying official default after declared eligibility checks
- **THEN** the requested image is one unbound auto-generated card, through the per-image gallery seam

#### Scenario: Pending policies do not trigger automatic recovery
- **WHEN** startup encounters a creation-pending character with an early named policy, with or without canonical ages
- **THEN** it enqueues no automatic portrait for that character, preserves any existing draft job/card for its normal settlement/reconnect path, and does not create an automatic replacement after reset

### Requirement: Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit
Creation and validated import SHALL establish named portrait policy transactionally. Unless creation explicitly skips generation, they SHALL schedule the guarded gallery callback through transaction.on_commit; actual enqueue SHALL require eligibility and unsatisfied gallery/job/official state. Rejected or rolled-back transactions SHALL emit no callback or job.

#### Scenario: A committed creation schedules exactly one guarded gallery request
- **WHEN** player creation commits successfully with generation not explicitly skipped
- **THEN** the character carries an explicit named policy with a stable key and exactly one
  post-commit guarded gallery request is scheduled

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
Every successful activation transport SHALL establish the same named portrait policy and apply the same explicit skip flag and guarded post-commit generation behavior. Official-satisfied, carded, in-flight or ineligible subjects SHALL enqueue nothing; skipped creation SHALL schedule nothing.

#### Scenario: Web activation assigns the portrait policy
- **WHEN** a character is activated through the Web creation flow
- **THEN** it has named policy with stable key str(pk); a callback is scheduled only when not explicitly skipped, and enqueue is subject to the shared guard

#### Scenario: Telnet and Web activation produce identical portrait state
- **WHEN** characters activate through Telnet and Web with equivalent skip, eligibility, gallery, job and official-reference inputs
- **THEN** both carry the same policy shape and the same guarded scheduling/enqueue outcome, including no request for skipped or satisfied subjects

#### Scenario: Rolled-back activation leaves no portrait state
- **WHEN** the activation transaction fails after the policy would have been assigned
- **THEN** no `portrait_policy` and no portrait job remain on the character

### Requirement: Validated named-NPC spawn schedules its guarded gallery request after the spawn transaction commits
The SceneBuilder spawn path SHALL schedule the guarded gallery request for a spawned occupant that carries an
explicit named portrait policy, through `transaction.on_commit`, so the schedule runs only after the
materialization transaction commits and an art failure can never roll back a materialized scene. A
spawned occupant with no policy (today's role-based scene NPCs and monsters) SHALL schedule nothing.

#### Scenario: A generic occupant schedules nothing
- **WHEN** a role-based scene NPC or monster is materialized
- **THEN** it carries no portrait policy and no post-commit portrait job is scheduled

#### Scenario: A named-policy occupant schedules after commit only
- **WHEN** a spawned occupant carries an explicit named portrait policy and the materialization
  commits
- **THEN** exactly one post-commit guarded gallery request is scheduled for that occupant's subject

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
  gallery request only when the subject has no card, no in-flight job, no satisfying official default, and either no gallery record
  or a record carrying a recorded error, nothing otherwise, and no fixed-output record is created

#### Scenario: A room without a resolvable archetype is a no-op
- **WHEN** a player enters a room with a `None` or unresolvable `scene_archetype`
- **THEN** no record or job is created and no error propagates to the player's move

### Requirement: Queue failure never rolls back gameplay
Any art failure in a lifecycle seam — startup sync, recovery, creation, import, spawn, or room entry —
SHALL log a bounded diagnostic and SHALL NOT roll back or otherwise alter the gameplay transaction it
accompanies. The asset simply remains `missing`/`failed` for the next idempotent ensure. Every
`transaction.on_commit` art callback SHALL be an exception-safe wrapper.

#### Scenario: An art failure during creation leaves the creation committed
- **WHEN** the post-commit guarded gallery request fails while player creation already committed
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
the failing field when either value is missing or non-integer. `world/art/service.py` SHALL run this check immediately before enqueue, except an owned pending-character request with a validated draft-portrait input SHALL validate submitted apparent age instead, without writing canonical ages.

#### Scenario: A valid integer record reaches the worker fixture
- **WHEN** a character with `age = 22` and `apparent_age = 22` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes and a fixture worker receives a job whose description contains the
  character's canonical identity

#### Scenario: A zero age is a valid canonical value
- **WHEN** a character with `age = 0` and `apparent_age = 0` and an explicit named portrait policy is
  enqueued
- **THEN** the age check passes, as zero lies within the canonical 0..10000 age range

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

#### Scenario: The draft-value exception is pending-only
- **WHEN** a character without canonical ages requests a portrait
- **THEN** only an owned pending-character request with the validated draft-portrait input can enqueue; an activated request or ordinary lifecycle request still rejects before render/write

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

### Requirement: Startup synchronization requests gallery art for every registered scene and species
Startup SHALL synchronize every registered scene archetype and visual species through the shared guarded gallery request after prune and seed synchronization. Existing cards, in-flight jobs, official-satisfied subjects and deliberately emptied scene galleries SHALL remain unchanged. One subject failure SHALL NOT abort startup.

#### Scenario: Registered subjects use the shared guard
- **WHEN** startup visits a synthetic scene and species registry
- **THEN** only unsatisfied eligible subjects request jobs, and repeated synchronization creates no duplicates

#### Scenario: Deletion and seeds survive synchronization
- **WHEN** a scene has a deliberately deleted card or a species holds a seed card
- **THEN** no automatic request replaces either decision

#### Scenario: One enqueue fails
- **WHEN** a request raises for one registered subject
- **THEN** the facade diagnostic identifies that subject and other subjects continue

### Requirement: Automatic generation publishes gallery defaults only
Every automatic path SHALL use the shared gallery request and official-satisfied guard for every gallery-bearing kind. An eligible unsatisfied subject SHALL request one unbound image from its standard deterministic description, with no free text or face rectangle. Settlement SHALL establish a default only under the declared gallery cap and preserve explicit official preferences.

#### Scenario: A committed creation produces one unbound default card
- **WHEN** eligible player creation commits without skipping or satisfying official artwork and its requested post-commit job is drained
- **THEN** the character's gallery holds exactly one unbound card carrying the fitted default square for its image, that card is the default, and no fixed-output record exists

#### Scenario: A registered monster tier produces one unbound default card
- **WHEN** startup synchronization runs for a registered monster visual species with an empty gallery, no job and no satisfying official default and its requested job is drained
- **THEN** that species' gallery holds exactly one unbound card carrying the fitted default square for its image, that card is the default, and startup wrote no fixed-output record

#### Scenario: The age gate still rejects before any record or prompt
- **WHEN** an automatic path runs for a character whose `age` or `apparent_age` is missing or non-integer
- **THEN** nothing is queued, no prompt is rendered, no card is appended, and the named diagnostic is logged

#### Scenario: A kind without the age precondition reads no age attribute
- **WHEN** an otherwise unsatisfied automatic path runs for a registered monster visual species
- **THEN** no canonical-age check runs, no age attribute is read, and the request proceeds

#### Scenario: A rolled-back transaction produces nothing
- **WHEN** a creation, import, or materialization transaction rolls back
- **THEN** the on-commit callback never fires, no gallery job exists, and no card is appended

#### Scenario: An art failure never rolls back gameplay
- **WHEN** the gallery request or its job fails on an automatic path
- **THEN** the creation, import, spawn, move, or startup is still reported as successful and a bounded diagnostic is logged

#### Scenario: The description is authored appearance only, for field-selecting kinds
- **WHEN** the automatic request targets a kind that declares field-selection support
- **THEN** the description is the authored appearance contribution and nothing else, expressed as the
  `appearance` field alone

#### Scenario: The description is registry-driven, for non-selecting kinds
- **WHEN** the automatic request targets a kind that declares no field selection
- **THEN** the description is that kind's registry-driven description with no selection supplied at all

#### Scenario: The requirement binds the description, not the argument shape
- **WHEN** compliance with this requirement is judged
- **THEN** the requirement is on the resulting description, not on the request's argument shape

#### Scenario: The first card is the default automatically
- **WHEN** the unbound card is the subject's first card
- **THEN** it becomes the subject's default automatically

#### Scenario: Each path keeps its existing guarantees unchanged
- **WHEN** an automatic path is wired to the gallery request
- **THEN** it keeps the canonical-age check at schedule time and again immediately before the queue
  write for every kind that declares the age precondition, the `transaction.on_commit` registration on
  the paths that have one, and the total failure isolation in which an art failure never rolls back
  creation, import, spawn, movement, or startup

#### Scenario: The unbound card takes the fitted default square
- **WHEN** the automatic request settles
- **THEN** the resulting card takes the fitted default square computed from the settled image's
  recorded pixel size

#### Scenario: Only gallery job records on generation paths
- **WHEN** any gallery-bearing subject goes through these automatic paths
- **THEN** an accepted request produces only a per-image gallery job; skipped, ineligible or satisfied paths produce no state

#### Scenario: Official selection survives settlement
- **WHEN** an automatic or manual request settles after an explicit official choice was stored
- **THEN** the choice remains selected and still outranks the generated default
