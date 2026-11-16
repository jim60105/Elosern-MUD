## MODIFIED Requirements

### Requirement: The background-removal stage emits boundary events
Each applied cutout attempt SHALL emit exactly one named-import facade event, art_cutout_done on success or art_cutout_failed with exc on failure. Context SHALL include subject and gallery image id plus fixed model identity. Skipped attempts SHALL emit neither event; the observability freeze SHALL gain no entry.

#### Scenario: A successful cutout leaves one info event
- **WHEN** an enabled portrait job's cutout succeeds
- **THEN** exactly one `art_cutout_done` event is logged carrying the job, subject,
  image id, model, and a duration, and no `art_cutout_failed` event is logged

#### Scenario: A failed cutout leaves one warn event with the exception
- **WHEN** an enabled portrait job's cutout raises
- **THEN** exactly one `art_cutout_failed` event is logged carrying the bounded code, the
  job, subject, image id, and model, and its rendered line carries the exception type,
  message, and origin frame in its `tb:` segment

#### Scenario: A skipped subject leaves no cutout event
- **WHEN** a scene job runs with the stage enabled, and separately a portrait job runs
  with the stage disabled
- **THEN** neither `art_cutout_done` nor `art_cutout_failed` is logged for either job

#### Scenario: Both events carry the shared context dict
- **WHEN** either boundary event is emitted
- **THEN** its context dict carries the `job` key, the full `subject`, the `image_id`
  (the gallery image id of the claimed job), and the
  fixed `model` value `bria-rmbg`
- **AND** `art_cutout_done` additionally carries the elapsed duration and
  `art_cutout_failed` additionally carries the bounded `code`

#### Scenario: The cutout module raises rather than logs
- **WHEN** a removal fails inside `world/art/cutout.py`
- **THEN** the module raises rather than logs, so exactly one event is emitted per
  outcome and no failure is reported twice

#### Scenario: The pair reports the stage outcome, not the job outcome
- **WHEN** a job's removal succeeds and its later encode or publish fails
- **THEN** it logs `art_cutout_done` followed by the existing generation-error and
  settle events, and this is NOT reduced to a single job-level event

## ADDED Requirements

### Requirement: Gallery portraits publish background-removed artifacts
Enabled portrait background removal SHALL apply to gallery-job PNG bytes for the declared character/monster allowlist before encoding and publication. Scenes and disabled removal SHALL pass bytes unchanged. The resulting card SHALL reference the single transparent artifact.

#### Scenario: A character portrait is stored transparent
- **WHEN** the stage is enabled with an injected backend, the sd-webui double returns an
  opaque multi-pixel PNG, and a gallery `portrait:character:<key>` job generates
  successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/character/<key><extension>` decodes with an alpha channel carrying fully
  transparent pixels, its bytes differ from the same job's disabled-stage output, and the
  backend recorded exactly one call

#### Scenario: A monster portrait is stored transparent
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a gallery `portrait:monster:<visual-key>` job for a registered visual species generates successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/monster/<visual-key><extension>` decodes with an alpha channel carrying fully
  transparent pixels, and its bytes differ from the same job's disabled-stage output

#### Scenario: A gallery portrait job is cut out on the same terms
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a gallery job for a character subject and a gallery job for a monster subject each
  generate successfully
- **THEN** each appends exactly one card whose stored
  `gallery/<kind-directory>/<subject-key>/<image-id><extension>` file decodes with a
  transparent alpha channel differing from its disabled-stage output, and no fixed-output
  record's committed output was touched

#### Scenario: Scene art never reaches the backend
- **WHEN** the stage is enabled and a `scene:<archetype>` job generates successfully
- **THEN** the injected backend recorded zero calls and the stored scene bytes are
  byte-for-byte equal to the bytes the same job produces with `ART_REMBG_ENABLED` false

#### Scenario: The disabled stage changes nothing
- **WHEN** `ART_REMBG_ENABLED` is false and a character portrait, a monster portrait, a
  gallery portrait job, and a scene job each generate successfully
- **THEN** the injected backend recorded zero calls and every stored artifact is
  byte-for-byte equal to the pre-change pipeline's output

#### Scenario: Every subject kind is classified by the allowlist
- **WHEN** the members of `ArtSubjectKind` are enumerated
- **THEN** each member is either present in `CUTOUT_SUBJECT_KINDS` or asserted absent by
  the contract test, so introducing a new kind fails the suite until it is classified

#### Scenario: One file per output across every consumer
- **WHEN** a portrait is generated, encoded, written, and published with the stage
  applied
- **THEN** the store, media route, presenter, and gallery card all reference exactly one
  file per output, as they did before the stage existed

#### Scenario: Every gallery portrait uses the same cutout gate
- **WHEN** a character or registered monster gallery job generates
- **THEN** the claimed subject allowlist and setting control cutout before its only per-image publication

#### Scenario: A kind outside the allowlist never touches the backend machinery
- **WHEN** a job for a subject kind outside the allowlist — `ArtSubjectKind.SCENE` in
  particular — settles with the stage enabled
- **THEN** no backend is resolved, no session is built, and no call is made, so the scene
  output stays byte-for-byte identical to the pre-change pipeline

#### Scenario: Disabling the stage leaves the pipeline byte-for-byte unchanged
- **WHEN** `ART_REMBG_ENABLED` is false
- **THEN** no subject of any kind reaches the backend and the entire pipeline is
  byte-for-byte unchanged

#### Scenario: Transparency tests drive an opaque multi-pixel fixture
- **WHEN** a test asserts that a stored portrait is transparent
- **THEN** it drives the sd-webui double with an OPAQUE, multi-pixel PNG fixture — never
  `fake_sd_client.DEFAULT_PNG`, which is a 1x1 already-transparent image and would
  satisfy the assertion with the stage disabled
- **AND** it asserts the stored bytes differ from the same job's disabled-stage output,
  so the transparency demonstrably originates in this stage

#### Scenario: The allowlist contains exactly the two portrait kinds
- **WHEN** the members of the closed `CUTOUT_SUBJECT_KINDS` allowlist are inspected
- **THEN** it contains exactly `ArtSubjectKind.CHARACTER` and `ArtSubjectKind.MONSTER`

#### Scenario: The allowlist is a membership test, never a SCENE negation
- **WHEN** the allowlist gate is implemented and maintained
- **THEN** it is an explicit membership test, never the negation of `ArtSubjectKind.SCENE`,
  so a subject kind added later must be classified deliberately rather than inheriting a
  cutout by default

### Requirement: Gallery cutout failure preserves existing cards
Cutout failures SHALL retain the bounded art_cutout_unavailable/art_cutout_error taxonomy, append no degraded card, preserve existing gallery cards/bytes and record the error on gallery state. Current terminal jobs SHALL be deleted. The stage SHALL perform no retry.

#### Scenario: An unavailable backend settles a bounded failure
- **WHEN** the stage is enabled, `ART_REMBG_BACKEND` names an unimportable dotted path,
  and a character portrait job runs
- **THEN** the record settles `failed` with `art_cutout_unavailable`, its prior valid
  output file is unchanged on disk, and no new file was written

#### Scenario: A removal failure settles a bounded failure
- **WHEN** the injected backend raises `CutoutError("art_cutout_error", …)` for a claimed
  portrait job
- **THEN** the record settles `failed` with `art_cutout_error` and the prior valid output
  is retained

#### Scenario: An unexpected backend exception is still bounded
- **WHEN** the injected backend raises an arbitrary non-`CutoutError` exception
- **THEN** the record settles `failed` with a bounded cutout code — never an unbounded
  exception and never `in_progress`

#### Scenario: A failing gallery cutout appends no card
- **WHEN** a claimed gallery portrait job's cutout fails with either bounded code
- **THEN** the subject's gallery holds the same cards it held before, the bounded code is
  recorded on the gallery record, and no file is referenced by any card

#### Scenario: One failing portrait does not fail its batch
- **WHEN** a claimed batch holds a scene job, a portrait job whose cutout fails, and a
  second portrait job whose cutout succeeds
- **THEN** the scene settles `done` unchanged, the failing portrait settles `failed` with
  its bounded code, the second portrait settles `done` with a transparent artifact, and no
  job is left `in_progress`

#### Scenario: A failed cutout never stores the un-cut image
- **WHEN** a portrait job's cutout fails after a successful generation
- **THEN** no artifact is written for that job, the sd-webui client was called exactly
  once, and the record's status carries the cutout code rather than `done`

#### Scenario: art_cutout_unavailable names backend-readiness failures
- **WHEN** the backend or its model could not be made ready: an unresolvable or
  unconstructible `ART_REMBG_BACKEND` dotted path, a failed `rembg` or `onnxruntime`
  import, a session build or model download failure, or a model absent from
  `ART_REMBG_MODEL_DIR` while `ART_REMBG_DOWNLOAD_ENABLED` is false
- **THEN** the surfaced code is `art_cutout_unavailable`

#### Scenario: art_cutout_error names removal failures
- **WHEN** the backend was ready and the removal itself failed: input the backend could
  not decode, an inference failure, or a returned value that fails the seam's PNG
  validation
- **THEN** the surfaced code is `art_cutout_error`

#### Scenario: A failed stage never re-runs the generation
- **WHEN** the stage fails after the sd-webui generation has already completed
- **THEN** the stage does not re-issue, retry, or fail the generation itself and no HTTP
  request is repeated

#### Scenario: Silent degradation is forbidden in favor of a visible retry
- **WHEN** the stage fails and the engine considers what to store
- **THEN** the un-cut original image is not stored — a stored opaque portrait would be
  indistinguishable from a stored cutout — and the failure is made visible and retryable
  through the existing `@art retry` path instead

## REMOVED Requirements

### Requirement: Character and monster portraits are stored with their background removed
**Reason**: Replaced by Gallery portraits publish background-removed artifacts; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: A background-removal failure is a bounded, terminal, non-degrading job failure
**Reason**: Replaced by Gallery cutout failure preserves existing cards; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.
