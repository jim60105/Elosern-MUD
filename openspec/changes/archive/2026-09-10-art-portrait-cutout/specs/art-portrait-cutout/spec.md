## ADDED Requirements

### Requirement: Character and monster portraits are stored with their background removed

`world/art/cutout.py` SHALL provide a background-removal stage that
`world/art/worker.py::_settle_one` applies to the PNG bytes returned by the sd-webui
client, BEFORE `world/art/formats.py::encode(...)`, so the encoded, written, and
published artifact is the transparent-background cutout and the store, media route,
presenter, and gallery card all reference exactly one file per output as they do today.
The stage SHALL be applied when, and only when, ALL of the following hold: the setting
`ART_REMBG_ENABLED` is true, and the claimed record's subject kind is a member of the
module's closed `CUTOUT_SUBJECT_KINDS` allowlist, which SHALL contain exactly
`ArtSubjectKind.CHARACTER` and `ArtSubjectKind.MONSTER`. The allowlist SHALL be an
explicit membership test, never the negation of `ArtSubjectKind.SCENE`, so a subject kind
added later must be classified deliberately rather than inheriting a cutout by default.

The gate SHALL be the subject kind derived from the claimed record, so it covers BOTH
publication paths identically: the classic per-subject identities
`portrait/character/<key><extension>` and `portrait/monster/<key><extension>`, and the
gallery per-image identity `gallery/<kind-directory>/<subject-key>/<image-id><extension>`.
A gallery portrait SHALL NOT differ from a classic portrait in cutout treatment.

A subject kind outside the allowlist — `ArtSubjectKind.SCENE` in particular — SHALL NOT
reach the backend at all: no backend is resolved, no session is built, and no call is
made, so scene output stays byte-for-byte identical to the pre-change pipeline. When
`ART_REMBG_ENABLED` is false, no subject of any kind reaches the backend and the entire
pipeline is byte-for-byte unchanged.

Every test asserting that a stored portrait is transparent SHALL drive the sd-webui
double with an OPAQUE, multi-pixel PNG fixture — never `fake_sd_client.DEFAULT_PNG`,
which is a 1x1 already-transparent image and would satisfy the assertion with the stage
disabled — and SHALL additionally assert that the stored bytes differ from the same
job's disabled-stage output, so the transparency demonstrably originates in this stage.

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

### Requirement: The background-removal backend is an injectable, CPU-only seam

`world/art/cutout.py` SHALL expose the backend through the settings `ART_REMBG_BACKEND`
dotted path (default `world.art.cutout.RembgCutoutBackend`), resolved exactly like
`ART_SD_CLIENT` is resolved by `resolve_sd_client()`, and SHALL expose a module-level
`remove_background(png_bytes) -> bytes` entry point that returns PNG bytes carrying an
alpha channel. `remove_background` SHALL validate the backend's return value before
returning it — a non-`bytes` value, empty bytes, bytes not beginning with the PNG
magic, or bytes that do not decode as an alpha-carrying PNG (`RGBA`/`LA`/`PA` mode)
SHALL raise `art_cutout_error` — so a misbehaving backend can never push a bad value
into `encode`, where it would surface as `sd_format_error` and blame the format
stage for a backend fault, and an opaque passthrough can never be stored as a
successful cutout. `world/art/fake_cutout.py` SHALL provide a deterministic
`FakeCutoutBackend` with the same interface that records every call, replays scripted
failures, and returns a real PNG whose alpha channel is zeroed over a fixed region —
never a passthrough of its input — without importing `rembg`, reading a model file, or
opening a socket. Tests and the browser harness SHALL inject the fake through
`ART_REMBG_BACKEND`, so no unit, integration, or browser test ever loads an ONNX model or
reaches the network.

`RembgCutoutBackend` SHALL import `rembg` and `onnxruntime` lazily, inside its first
call, never at module import, so `world/art/cutout.py` stays importable when the optional
stack is absent or broken. It SHALL build at most one inference session per configured
model per process, cached at module level behind a lock so concurrent or repeated jobs
reuse the ~3 s session build exactly once. It SHALL request only the
`CPUExecutionProvider`; no CUDA, TensorRT, or other GPU execution provider SHALL be
requested under any configuration. When `ART_REMBG_THREADS` is non-zero it SHALL be
applied as the session's ONNX intra-op thread count; zero SHALL leave ONNX Runtime's own
default in place.

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

### Requirement: A background-removal failure is a bounded, terminal, non-degrading job failure

Every failure of the stage SHALL surface as `CutoutError` carrying exactly one of two
bounded codes, and `world/art/worker.py` SHALL settle the claimed record `failed` with
that code:

- `art_cutout_unavailable` — the backend or its model could not be made ready: an
  unresolvable or unconstructible `ART_REMBG_BACKEND` dotted path, a failed `rembg` or
  `onnxruntime` import, a session build or model download failure, or a model absent from
  `ART_REMBG_MODEL_DIR` while `ART_REMBG_DOWNLOAD_ENABLED` is false.
- `art_cutout_error` — the backend was ready and the removal itself failed: input the
  backend could not decode, an inference failure, or a returned value that fails the
  seam's PNG validation.

`remove_background` SHALL map every escaping exception to one of these two codes, so no
unbounded exception reaches the worker. A classic record SHALL settle `failed` with the
code and SHALL retain its prior valid output, exactly as `sd_format_error` does today; a
gallery job SHALL settle through the gallery-failed path, appending NO card, recording the
bounded code on the subject's `GalleryRecord`, and leaving every existing card intact.
Other records in the same claimed batch SHALL be unaffected and no claimed job SHALL be
left `in_progress`. The stage SHALL NOT re-issue, retry, or fail the sd-webui generation
itself — the generation has already completed and no HTTP request is repeated.

The engine SHALL NOT store the un-cut original image when the stage fails: a stored
opaque portrait is indistinguishable from a stored cutout, so silent degradation is
forbidden and the failure is made visible and retryable through the existing
`@art retry` path instead.

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

### Requirement: The model artifact is cached in a code-only persistent directory under an explicit download policy

`ART_REMBG_MODEL_DIR` SHALL default to `<GAME_DIR>/server/.rembg` and SHALL NOT read any
environment variable — a mistyped value would silently relocate a ~1 GB artifact off the
persistent volume, the same rationale that keeps `ART_STORE_ROOT` code-only.
`secret_settings.py` remains its only override path. The backend SHALL create the
directory when absent and SHALL point `rembg`'s model home at it — setting the model-home
environment variables `rembg` reads before the lazy `rembg` import — so the default
`~/.rembg/models` location, which the container image maps onto a `tmpfs` `HOME`, is never
used.

`ART_REMBG_MODEL` SHALL be a closed, case-insensitive choice set containing exactly
`bria-rmbg`, `isnet-anime`, `isnet-general-use`, `u2net`, and `u2netp`, defaulting to
`bria-rmbg`. A value outside the set SHALL fail settings import with the named error
rather than failing every portrait job at runtime. The setting exists so the
BRIA-licensed `bria-rmbg` weight can be replaced by a permissively licensed alternative
with one environment variable and a requeue, with no code change; the settings comment and
the operator documentation SHALL state that commercial use of `bria-rmbg` requires a
licence from BRIA.

`ART_REMBG_DOWNLOAD_ENABLED` SHALL default to true. When false, the backend SHALL verify
that the configured model's artifact is already present under `ART_REMBG_MODEL_DIR`
before building a session and SHALL raise `art_cutout_unavailable` immediately when it is
absent — performing no `rembg` import, no network access, and no unbounded wait — so an
air-gapped or pre-seeded deployment gets a fast bounded failure instead of a download
attempt.

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

### Requirement: An output format that cannot carry alpha is refused at boot

`server/conf/settings.py` SHALL raise `django.core.exceptions.ImproperlyConfigured` at
settings import when `ART_REMBG_ENABLED` is true and the effective `ART_SD_OUTPUT_FORMAT`
is `jpeg`, naming both settings and stating that JPEG cannot carry the transparency the
stage produces. The check SHALL run AFTER the `secret_settings.py` import, alongside the
derived `ART_SD_OUTPUT_EXTENSION`, so every override path — code default, environment,
and `secret_settings.py` — is covered by the one check. The engine SHALL NOT silently
substitute a format, silently disable the stage, or store an image whose alpha was
discarded by the encoder: an RGB normalization would keep the original background while
the artifact claimed to be a cutout, which is a silent falsehood rather than a bounded
failure.

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

### Requirement: The background-removal stage emits boundary events

`world/art/worker.py` SHALL emit exactly one `world.observability` facade event per
applied cutout attempt: `art_cutout_done` at info level on success and
`art_cutout_failed` at warn level carrying the exception with `exc=` on failure. Both
SHALL carry a context dict with the `job` key, the full `subject`, the `image_id` (the
gallery image id for a gallery job, empty for a classic record), and the configured
`model`; `art_cutout_done` SHALL additionally carry the elapsed duration and
`art_cutout_failed` SHALL additionally carry the bounded `code`. `world/art/cutout.py`
SHALL raise rather than log, so exactly one event is emitted per outcome and no failure is
reported twice. No event SHALL be emitted for a subject the stage skipped. The pair
reports the STAGE outcome, not the job outcome: a job whose removal succeeded and whose
later encode or publish failed SHALL log `art_cutout_done` followed by the existing
generation-error and settle events, and this SHALL NOT be reduced to a single job-level
event. Production
modules SHALL use named facade imports so tests patch the caller module's binding, and
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
