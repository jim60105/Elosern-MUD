# art-queue-worker Specification

## Purpose
Defines the persisted asset-record contract (status, deterministic source hash, same-store output identity, attempt/error metadata, aspect ratio), the subject-keyed idempotent queue, and the shared serialization lock and single worker concurrency slot for scenes and portraits. Covers deterministic sd-webui generation confined to the store, settings-configurable scheduling, same-origin media serving that never exposes the store root, wire-stable in-flight status, and claim/settle boundary events.

## Requirements

### Requirement: The scheduler is settings-configurable and disableable
`world/art/scheduler.py` SHALL provide a persistent Script that drains up to the configured limit of
pending jobs at the configured interval. When `ART_SCHEDULER_ENABLED` is false the scheduler SHALL run
no drain, records SHALL remain `missing`/`pending`, truthful normal alpha/name-initial/bundled-scene fallbacks SHALL remain, and gameplay SHALL
proceed unchanged.

#### Scenario: The disabled scheduler never drains
- **WHEN** the scheduler is disabled and pending records exist
- **THEN** no drain runs, the records stay `pending`, and gameplay proceeds

#### Scenario: The enabled scheduler drains up to its limit per interval
- **WHEN** the scheduler is enabled with a limit and pending records exist
- **THEN** each interval drains at most the configured limit of pending records through the worker

#### Scenario: Disabled generation does not erase independent faults
- **WHEN** scheduler is disabled while a recorded failed job or required static resource is broken
- **THEN** resolution preserves independent truthful failure facts and required scene-art selection without scheduling new work

### Requirement: In-flight generation exposes a wire-stable status
The art presenter SHALL normalize the internal `in_progress` record status to a wire-accepted value
(`pending`) so a panel snapshot taken while a worker holds a claim never fails validation.

#### Scenario: Snapshot during generation shows a valid pending state
- **WHEN** a worker has claimed a record (status `in_progress`) and a full art snapshot is requested
- **THEN** the panel payload carries the wire-stable `pending` status (or an explicitly supported
  generating status) and the panel renders normally

#### Scenario: Settled statuses pass through unchanged
- **WHEN** a record is `missing`, `pending`, `failed`, or `done`
- **THEN** the presenter emits that status without normalization

### Requirement: Worker claim and settle emit boundary events

The art worker SHALL emit one `sd_job_claim` info event when it claims a
queue record and one `sd_job_settled` info event when the record settles,
with `job`, `subject`, and — on settle — `status` and the settle `reason`
code, through the `world.observability` facade. Claim/settle ordering,
idempotency, and the single-concurrency-slot invariant MUST NOT change.

#### Scenario: A generated asset leaves a claim/settle pair

- **WHEN** the worker claims one queued subject and generation settles
- **THEN** one `sd_job_claim` and one `sd_job_settled` event are logged with
  the job identity, subject, final status, and reason code

#### Scenario: A claim failure releases the slot visibly

- **WHEN** claiming raises and the worker releases its slot and re-raises
- **THEN** a facade event carries the exception before propagation, and no
  `sd_job_settled` event is emitted for the unclaimed record

### Requirement: Gallery jobs carry transient request state only
The queue SHALL persist one gallery job per requested image, containing typed subject identity, image id, pending card metadata, source description/hash, prompt digest, aspect ratio, status, attempt count, claim token and timestamps. Jobs SHALL hold no live entity or committed output identity. Terminal settlement SHALL delete the job and persist success or failure in gallery state.

#### Scenario: A request owns one transient job
- **WHEN** one gallery image is requested
- **THEN** a unique art:<full-subject-key>:gen:<image-id> job stores validated pending metadata and no output/prior-output/published-token/seed/hash-review fields

#### Scenario: Claim records a lease
- **WHEN** a pending job is claimed
- **THEN** it becomes in_progress with a fresh claim token, claimed timestamp and incremented attempts

#### Scenario: Settlement stores results in the gallery
- **WHEN** a job succeeds or fails
- **THEN** success appends a card with its own seed and prompt; failure records its bounded code without changing existing cards; both delete the job

#### Scenario: Expired claim recovers
- **WHEN** a claim lease expires
- **THEN** recovery returns the job to pending without changing cards or accepting an old claim result

### Requirement: Gallery image requests own independent queue jobs
Gallery enqueue SHALL create a distinct job for each accepted image request under one shared queue lock. Automatic idempotency SHALL belong to the shared gallery guard. Jobs SHALL validate current subject membership at enqueue, claim and settle. No subject-keyed generation queue or classic retry/reset path SHALL remain.

#### Scenario: Independent requests remain independent
- **WHEN** two explicit requests target one subject
- **THEN** two fresh image ids and distinct jobs exist; neither replaces the other

#### Scenario: Automatic requests remain guarded
- **WHEN** startup repeats for a carded, official-satisfied or in-flight subject
- **THEN** no additional image job is created

#### Scenario: Retired monster keys fail closed
- **WHEN** a queued monster key is no longer registered
- **THEN** no card is published for it and other subjects remain independent

#### Scenario: Failed keys represent gallery state
- **WHEN** failed_keys is requested after a job failed and was deleted
- **THEN** it returns canonical subject keys from recorded gallery errors, not deleted job ids or fixed-output records

### Requirement: Gallery jobs share one lock and worker slot
Scene and portrait gallery jobs SHALL share one serialization lock, pending ordering and worker slot. Claim and settlement SHALL run under the lock; background generation SHALL release it. Concurrent drains SHALL never run more than one generation, and gameplay enqueue SHALL not block across external I/O.

#### Scenario: Concurrent drains preserve one worker
- **WHEN** a drain runs while another drain and enqueue arrive
- **THEN** only one worker runs, enqueue can complete without waiting for the image service, and settlement is serialized

### Requirement: Gallery workers publish confined immutable image outputs
The worker SHALL generate one image per claimed gallery job through the bounded internal client, then remove background when applicable, encode, write and publish one immutable per-image output. Publication SHALL validate confinement and the current claim token. Failure SHALL preserve existing cards and bytes, record its bounded code and remove the spent job.

#### Scenario: Publication uses the per-image identity
- **WHEN** the injected client returns valid PNG bytes and configured encoding succeeds
- **THEN** one gallery/<declared-directory>/<subject-key>/<image-id><extension> card is published with returned prompt/seed and decoded dimensions; the job is removed

#### Scenario: Nullable seed belongs to the new card
- **WHEN** a response omits or malforms seed metadata
- **THEN** the new card stores seed None and never inherits the prior card seed

#### Scenario: Conversion and cutout failures preserve previous art
- **WHEN** encoding or enabled cutout fails
- **THEN** the named sd_format_error or art_cutout_* code is recorded, no card is appended, existing bytes remain, and the job is removed

#### Scenario: Atomic write survives interruption
- **WHEN** a write fails or the process dies before card publication
- **THEN** no existing card bytes are overwritten; temporary/unreferenced gallery files remain pruneable and no false card is published

#### Scenario: Stale claim cannot publish or fail the current job
- **WHEN** an expired worker reports success or failure after reclaim and a new claim
- **THEN** its obsolete token changes no card, current job or recorded error, and its temporary artifacts are cleaned

#### Scenario: Current claim validates its expected identity
- **WHEN** the output path is missing, symlinked, outside root or not the job's exact per-image identity
- **THEN** publication is rejected with a bounded error and no out-of-root file or card is written

#### Scenario: Provenance is captured once
- **WHEN** the prompt library changes after request construction
- **THEN** the appended card and embedded parameters describe the returned request values without re-rendering the library

#### Scenario: One failure cannot strand a batch
- **WHEN** a batch combines client, prompt, configuration, cutout and unexpected failures
- **THEN** each current job succeeds or records its bounded failure and is removed; none stays in_progress

#### Scenario: Lease covers the complete batch
- **WHEN** lease recovery evaluates a batch with configured generation/conversion/removal allowances
- **THEN** the bound includes every job and optional removal allowance; a still-valid batch is not reclaimed

#### Scenario: Client and conversion policy remain configurable
- **WHEN** ART_SD_CLIENT and output format are configured
- **THEN** the chosen injected client and encoder are used, the output extension follows the format, and disabled cutout passes transport bytes unchanged

#### Scenario: Replacement cleans only displaced gallery output
- **WHEN** a capped gallery publishes a new card using a different format
- **THEN** the new card/default commits before the old unreferenced gallery file is removed; uncapped galleries retain prior cards and files

### Requirement: Runtime media serves gallery card identities only
Runtime media SHALL serve only confined identities referenced by readable gallery cards. Missing, malformed, cross-subject, symlinked or out-of-root paths SHALL return 404. Fixed subject-output scene/portrait routes SHALL be absent. Official, bundled and alpha routes SHALL retain their existing distinct admission rules. Presenters SHALL expose no store root.

#### Scenario: Card authorization serves immutable output
- **WHEN** a readable gallery card references a confined image
- **THEN** its same-origin gallery route serves its bytes and an unreferenced file returns 404

#### Scenario: Removed routes cannot serve files
- **WHEN** a request addresses an old fixed scene or portrait identity
- **THEN** it returns 404 even if a file remains on disk

#### Scenario: Independent artwork routes survive
- **WHEN** an admitted official, bundled scene or alpha identity is requested
- **THEN** its existing fingerprint/confinement rules apply without requiring a generation record
