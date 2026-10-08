# art-portrait-cutout Specification

## Purpose
The portrait background-removal stage: a local CPU `rembg` post-process on
the sd-webui transport PNG bytes, applied between generation and encoding
for CHARACTER and MONSTER portraits only (classic records AND gallery
jobs), behind the injectable `ART_REMBG_BACKEND` seam with two bounded
failure codes, a cached one-session-per-model backend, a code-only
persistent model cache, the fail-closed jpeg alpha guard, and one boundary
event pair per stage outcome. Scenes never reach the backend. (Synced from
the archived `art-portrait-cutout` change.)

## Requirements

### Requirement: Character and monster portraits are stored with their background removed

`world/art/cutout.py` SHALL provide a background-removal stage that
`world/art/worker.py::_settle_one` applies to the PNG bytes returned by the sd-webui
client, BEFORE `world/art/formats.py::encode(...)`, so the encoded, written, and
published artifact is the transparent-background cutout. The stage SHALL be applied
when, and only when, `ART_REMBG_ENABLED` is true and the claimed record's subject kind
is a member of the module's closed `CUTOUT_SUBJECT_KINDS` allowlist.

#### Scenario: A character portrait is stored transparent
- **WHEN** the stage is enabled with an injected backend, the sd-webui double returns an
  opaque multi-pixel PNG, and a classic `portrait:character:<key>` job generates
  successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/character/<key><extension>` decodes with an alpha channel carrying fully
  transparent pixels, its bytes differ from the same job's disabled-stage output, and the
  backend recorded exactly one call

#### Scenario: A monster portrait is stored transparent
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a classic `portrait:monster:<tier>` job generates successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/monster/<tier><extension>` decodes with an alpha channel carrying fully
  transparent pixels, and its bytes differ from the same job's disabled-stage output

#### Scenario: A gallery portrait job is cut out on the same terms
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a gallery job for a character subject and a gallery job for a monster subject each
  generate successfully
- **THEN** each appends exactly one card whose stored
  `gallery/<kind-directory>/<subject-key>/<image-id><extension>` file decodes with a
  transparent alpha channel differing from its disabled-stage output, and no classic
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

#### Scenario: The gate covers both publication paths identically
- **WHEN** a portrait job settles through either the classic per-subject identity
  (`portrait/character/<key><extension>`, `portrait/monster/<key><extension>`) or the
  gallery per-image identity (`gallery/<kind-directory>/<subject-key>/<image-id><extension>`)
- **THEN** the gate is the subject kind derived from the claimed record, and a gallery
  portrait receives exactly the same cutout treatment as a classic portrait

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

### Requirement: The background-removal backend is an injectable, CPU-only seam

`world/art/cutout.py` SHALL expose the backend through the settings `ART_REMBG_BACKEND`
dotted path (default `world.art.cutout.RembgCutoutBackend`), resolved exactly like
`ART_SD_CLIENT` is resolved by `resolve_sd_client()`, and SHALL expose a module-level
`remove_background(png_bytes) -> bytes` entry point that returns PNG bytes carrying an
alpha channel. `remove_background` SHALL validate the backend's return value before
returning it and SHALL raise `art_cutout_error` on any invalid return.

#### Scenario: The configured backend is the one that runs
- **WHEN** `ART_REMBG_BACKEND` names the fake and an enabled portrait job runs
- **THEN** the fake recorded the call, its cut-out bytes are what reached `encode`, and no
  `rembg` import occurred

#### Scenario: Only the CPU execution provider is requested
- **WHEN** the real backend builds its session with the ONNX session factory patched
- **THEN** the requested provider list is exactly `["CPUExecutionProvider"]`

#### Scenario: The session is built once per process
- **WHEN** the real backend removes backgrounds for three images in a row with the
  session factory patched
- **THEN** the session factory was invoked exactly once and the same session object
  served all three calls

#### Scenario: A backend returning non-PNG bytes is caught at the seam
- **WHEN** an injected backend returns a non-`bytes` value, empty bytes, or bytes without
  the PNG magic
- **THEN** `remove_background` raises `CutoutError` with code `art_cutout_error`, and the
  value never reaches `encode` (the settled code is the cutout code, never
  `sd_format_error`)

#### Scenario: A backend passthrough of an opaque PNG is caught at the seam
- **WHEN** an injected backend returns the original opaque RGB PNG unchanged, or any
  decodable PNG whose mode carries no alpha
- **THEN** `remove_background` raises `CutoutError` with code `art_cutout_error` and the
  bytes never reach `encode`, so a non-cutout can never be stored as a successful cutout

#### Scenario: The module imports without the optional stack
- **WHEN** `world.art.cutout` is imported in an environment where importing `rembg` raises
- **THEN** the import succeeds and the failure surfaces only when a removal is attempted

#### Scenario: The configured thread cap reaches the session options
- **WHEN** `ART_REMBG_THREADS` is `4` and the real backend builds its session with the
  ONNX session factory patched
- **THEN** the session options carry an intra-op thread count of `4`, and with the
  setting at `0` no thread cap is applied and ONNX Runtime's own default stands (the
  mechanism by which the cap reaches the session is whichever the locked `rembg` version
  supports; the requirement is the observable outcome, not a particular call signature)

#### Scenario: One session per configured model, shared behind a module-level lock
- **WHEN** concurrent or repeated jobs run against the real backend
- **THEN** at most one inference session is built per configured model per process,
  cached at module level behind a lock, so the ~3 s session build is reused exactly once

#### Scenario: FakeCutoutBackend is deterministic and dependency-free
- **WHEN** `world/art/fake_cutout.py`'s `FakeCutoutBackend` is used
- **THEN** it exposes the same interface, records every call, replays scripted failures,
  and returns a real PNG whose alpha channel is zeroed over a fixed region — never a
  passthrough of its input — without importing `rembg`, reading a model file, or opening
  a socket
- **AND** tests and the browser harness inject the fake through `ART_REMBG_BACKEND`, so
  no unit, integration, or browser test ever loads an ONNX model or reaches the network

#### Scenario: The real backend imports its stack lazily
- **WHEN** `RembgCutoutBackend` is constructed and later performs its first removal
- **THEN** it imports `rembg` and `onnxruntime` lazily, inside its first call, never at
  module import, so `world/art/cutout.py` stays importable when the optional stack is
  absent or broken

#### Scenario: A bad backend value never blames the format stage
- **WHEN** a misbehaving backend pushes a bad value toward `encode`
- **THEN** the seam's validation raises first, so the value never reaches `encode` where
  it would surface as `sd_format_error` and blame the format stage for a backend fault
- **AND** an opaque passthrough can never be stored as a successful cutout

#### Scenario: Seam validation enumerates the invalid returns
- **WHEN** the backend's return is a non-`bytes` value, empty bytes, bytes not beginning
  with the PNG magic, or bytes that do not decode as an alpha-carrying PNG (`RGBA`/`LA`/
  `PA` mode)
- **THEN** `remove_background` raises `art_cutout_error` before returning it

#### Scenario: No GPU provider is ever requested
- **WHEN** the real backend builds its session under any configuration
- **THEN** it requests only the `CPUExecutionProvider`; no CUDA, TensorRT, or other GPU
  execution provider is requested

#### Scenario: The thread cap reaches the session or defers to the default
- **WHEN** `ART_REMBG_THREADS` is non-zero
- **THEN** it is applied as the session's ONNX intra-op thread count; zero leaves ONNX
  Runtime's own default in place

### Requirement: A background-removal failure is a bounded, terminal, non-degrading job failure

Every failure of the stage SHALL surface as `CutoutError` carrying exactly one of two
bounded codes — `art_cutout_unavailable` or `art_cutout_error` — and
`world/art/worker.py` SHALL settle the claimed record `failed` with that code.
`remove_background` SHALL map every escaping exception to one of these two codes, so no
unbounded exception reaches the worker. A failure is terminal and non-degrading: the
stage never retries and the engine never stores a degraded artifact.

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

#### Scenario: A classic failure retains its prior valid output
- **WHEN** a classic record's cutout fails
- **THEN** the record settles `failed` with the bounded code and retains its prior valid
  output, exactly as `sd_format_error` does today

#### Scenario: A failed stage never re-runs the generation
- **WHEN** the stage fails after the sd-webui generation has already completed
- **THEN** the stage does not re-issue, retry, or fail the generation itself and no HTTP
  request is repeated

#### Scenario: Silent degradation is forbidden in favor of a visible retry
- **WHEN** the stage fails and the engine considers what to store
- **THEN** the un-cut original image is not stored — a stored opaque portrait would be
  indistinguishable from a stored cutout — and the failure is made visible and retryable
  through the existing `@art retry` path instead

### Requirement: The model artifact is cached in a code-only persistent directory under an explicit download policy

`ART_REMBG_MODEL_DIR` SHALL default to `<GAME_DIR>/server/.rembg` and SHALL NOT read any
environment variable; `secret_settings.py` remains its only override path. The backend
SHALL create the directory when absent and SHALL point `rembg`'s model home at it.
`ART_REMBG_MODEL` SHALL be a closed, case-insensitive choice set containing exactly
`bria-rmbg`, `isnet-anime`, `isnet-general-use`, `u2net`, and `u2netp`, defaulting to
`bria-rmbg`. `ART_REMBG_DOWNLOAD_ENABLED` SHALL default to true.

#### Scenario: The model home follows the setting, not the home directory
- **WHEN** the real backend prepares a session with the `rembg` session factory patched
- **THEN** the model-home environment variables it sets equal `ART_REMBG_MODEL_DIR`, that
  directory exists, and no path under `$HOME` was used

#### Scenario: A model name outside the closed set fails the boot
- **WHEN** the settings module is imported with `ART_REMBG_MODEL=segment-anything`
- **THEN** the import raises `ImproperlyConfigured` naming `ART_REMBG_MODEL`, quoting the
  value, and listing the accepted set, and no value falls back silently

#### Scenario: An environment model-directory variable is ignored
- **WHEN** the settings module is imported with `ART_REMBG_MODEL_DIR` set in the
  environment
- **THEN** the effective value remains the `server/.rembg` path under `GAME_DIR` and no
  environment read for that name occurs

#### Scenario: Downloads disabled with no cached model fails fast
- **WHEN** `ART_REMBG_DOWNLOAD_ENABLED` is false, no model artifact exists under
  `ART_REMBG_MODEL_DIR`, and a portrait job runs with the real backend
- **THEN** the job settles `failed` with `art_cutout_unavailable`, no `rembg` import was
  performed, and no network access was attempted

#### Scenario: The code-only rationale matches ART_STORE_ROOT
- **WHEN** `ART_REMBG_MODEL_DIR` resolves its effective value
- **THEN** no environment variable is read — a mistyped value would silently relocate a
  ~1 GB artifact off the persistent volume, the same rationale that keeps
  `ART_STORE_ROOT` code-only

#### Scenario: The backend redirects rembg's model home off tmpfs HOME
- **WHEN** the backend prepares `rembg`
- **THEN** it sets the model-home environment variables `rembg` reads before the lazy
  `rembg` import, so the default `~/.rembg/models` location — which the container image
  maps onto a `tmpfs` `HOME` — is never used

#### Scenario: An out-of-set model fails boot, not every portrait job
- **WHEN** `ART_REMBG_MODEL` is set outside the closed set
- **THEN** settings import fails with the named error rather than every portrait job
  failing at runtime

#### Scenario: The model swap is licensing-driven and documented
- **WHEN** operators need to replace the BRIA-licensed `bria-rmbg` weight with a
  permissively licensed alternative
- **THEN** one environment variable and a requeue suffice, with no code change
- **AND** the settings comment and the operator documentation state that commercial use
  of `bria-rmbg` requires a licence from BRIA

#### Scenario: Downloads disabled verifies the cache before the session
- **WHEN** `ART_REMBG_DOWNLOAD_ENABLED` is false
- **THEN** the backend verifies the configured model's artifact is already present under
  `ART_REMBG_MODEL_DIR` before building a session and raises `art_cutout_unavailable`
  immediately when it is absent — performing no `rembg` import, no network access, and no
  unbounded wait — so an air-gapped or pre-seeded deployment gets a fast bounded failure
  instead of a download attempt

### Requirement: An output format that cannot carry alpha is refused at boot

`server/conf/settings.py` SHALL raise `django.core.exceptions.ImproperlyConfigured` at
settings import when `ART_REMBG_ENABLED` is true and the effective `ART_SD_OUTPUT_FORMAT`
is `jpeg`, naming both settings and stating that JPEG cannot carry the transparency the
stage produces. The check SHALL run AFTER the `secret_settings.py` import, alongside the
derived `ART_SD_OUTPUT_EXTENSION`, so every override path is covered by the one check.

#### Scenario: The alpha-hostile combination fails the boot
- **WHEN** the settings module is imported with `ART_REMBG_ENABLED=true` and
  `ART_SD_OUTPUT_FORMAT=jpeg`
- **THEN** the import raises `ImproperlyConfigured` naming both `ART_REMBG_ENABLED` and
  `ART_SD_OUTPUT_FORMAT`, and no partially configured settings module is usable

#### Scenario: A secret-file format override is caught by the same check
- **WHEN** `ART_REMBG_ENABLED=true` is set with no format variable and
  `secret_settings.py` assigns `ART_SD_OUTPUT_FORMAT = "jpeg"`
- **THEN** the import fails with the same named error, because the check runs after the
  secret import

#### Scenario: The alpha-capable formats boot normally
- **WHEN** the settings module is imported with `ART_REMBG_ENABLED=true` and
  `ART_SD_OUTPUT_FORMAT` set to `png`, then `webp`, then `avif`
- **THEN** all three imports succeed

#### Scenario: JPEG alone is still a supported configuration
- **WHEN** the settings module is imported with `ART_SD_OUTPUT_FORMAT=jpeg` and
  `ART_REMBG_ENABLED` false or absent
- **THEN** the import succeeds unchanged

#### Scenario: One check covers every override path
- **WHEN** the effective `ART_SD_OUTPUT_FORMAT` is set by any of code default,
  environment, or `secret_settings.py`
- **THEN** the one check placed after the secret import and alongside the derived
  `ART_SD_OUTPUT_EXTENSION` covers every path

#### Scenario: No silent format substitution or alpha-discarding store
- **WHEN** the stage is enabled and the effective output format cannot carry alpha
- **THEN** the engine does not silently substitute a format, silently disable the stage,
  or store an image whose alpha was discarded by the encoder — an RGB normalization
  would keep the original background while the artifact claimed to be a cutout, which is
  a silent falsehood rather than a bounded failure

### Requirement: The background-removal stage emits boundary events

`world/art/worker.py` SHALL emit exactly one `world.observability` facade event per
applied cutout attempt: `art_cutout_done` at info level on success and
`art_cutout_failed` at warn level carrying the exception with `exc=` on failure. No
event SHALL be emitted for a subject the stage skipped. Production modules SHALL use
named facade imports so tests patch the caller module's binding, and
`tools/observability_freeze.json` SHALL gain no entry.

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
  (the gallery image id for a gallery job, empty for a classic record), and the
  configured `model`
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
