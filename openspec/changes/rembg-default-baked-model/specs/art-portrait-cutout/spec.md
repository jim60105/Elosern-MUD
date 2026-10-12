# Spec Delta

## MODIFIED Requirements

### Requirement: The background-removal backend is an injectable, CPU-only seam

`world/art/cutout.py` SHALL expose the backend via the `ART_REMBG_BACKEND` setting (default
`world.art.cutout.RembgCutoutBackend`), resolved like `resolve_sd_client()`, and a
module-level `remove_background(png_bytes) -> bytes` returning alpha-carrying PNG bytes.
`remove_background` SHALL validate that return, raising `art_cutout_error` on an invalid
one. The real backend SHALL use rembg's default `bria-rmbg`, take no model-selection
parameter, and reuse one session per process.

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
- **THEN** at most one default-model inference session is built per process, cached at
  module level behind a lock and shared by every real-backend instance
- **AND** inference calls do not hold the session-construction lock

#### Scenario: FakeCutoutBackend is deterministic and dependency-free
- **WHEN** `world/art/fake_cutout.py`'s `FakeCutoutBackend` is used
- **THEN** it exposes the same interface, records every call, replays scripted failures,
  and returns a real PNG whose alpha channel is zeroed over a fixed region without
  importing `rembg`, reading a model file, or opening a socket
- **AND** it never returns its input unchanged
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

#### Scenario: The default model is selected without a model argument
- **WHEN** the real backend constructs its session with the session factory patched
- **THEN** no positional model name or model-name keyword is supplied, the CPU execution
  provider remains the sole requested provider, and the locked library default is `bria-rmbg`
- **AND** no `ART_REMBG_MODEL` setting or override is consulted

### Requirement: The background-removal stage emits boundary events

`world/art/worker.py` SHALL emit exactly one `world.observability` facade event per applied
cutout attempt: `art_cutout_done` at info level on success and `art_cutout_failed` at warn
level carrying the exception with `exc=`. No event SHALL be emitted for a skipped subject.
Production modules SHALL use named facade imports so tests patch the caller module's
binding, and `tools/observability_freeze.json` SHALL gain no entry. The `model` context value
SHALL be the fixed `bria-rmbg` identity.

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

## REMOVED Requirements

### Requirement: The model artifact is cached in a code-only persistent directory under an explicit download policy

**Reason**: The configurable model-choice contract and its licence-driven model-swap scenarios are removed. The replacement contract fixes the default weight and permits baked image delivery.

**Migration**: Update the four annotations in `world/art/tests/test_cutout.py` to `art-portrait-cutout::the-default-removal-model-has-a-code-only-home-and-an-explicit-runtime-download-policy`. Remove the model setting and its callers; no runtime data migration or compatibility alias is introduced.

## ADDED Requirements

### Requirement: The default removal model has a code-only home and an explicit runtime download policy

`ART_REMBG_MODEL_DIR` SHALL default to `<GAME_DIR>/server/.rembg` without an environment
reader; `secret_settings.py` remains its only override path. The backend SHALL use this
home for the sole `bria-rmbg` artifact. `ART_REMBG_DOWNLOAD_ENABLED` SHALL default to true
and govern missing-artifact runtime acquisition only. The standard image SHALL supply
the artifact before runtime and SHALL require no model download with either switch value.

#### Scenario: The model home follows the setting, not the home directory
- **WHEN** the real backend prepares a session with the rembg session factory patched
- **THEN** the model-home environment variables it sets equal `ART_REMBG_MODEL_DIR`, that
  directory exists, and no path under `$HOME` was used

#### Scenario: The former model variable has no effect
- **WHEN** settings are imported with `ART_REMBG_MODEL=ISNET-ANIME`, then separately
  `ART_REMBG_MODEL=segment-anything`, then separately without that variable
- **THEN** each import succeeds without a model-choice validation error, the project
  defines no `ART_REMBG_MODEL` setting, and the real backend still uses `bria-rmbg`

#### Scenario: An environment model-directory variable is ignored
- **WHEN** the settings module is imported with `ART_REMBG_MODEL_DIR` set in the environment
- **THEN** the effective value remains the `server/.rembg` path under `GAME_DIR` and no
  environment read for that name occurs

#### Scenario: Downloads disabled with no default artifact fails fast
- **WHEN** `ART_REMBG_DOWNLOAD_ENABLED` is false, no default-model artifact exists under
  `ART_REMBG_MODEL_DIR`, and a portrait job runs with the real backend
- **THEN** the job settles `failed` with `art_cutout_unavailable`, no rembg import was
  performed, and no network access was attempted

#### Scenario: Unrelated model artifacts cannot satisfy readiness
- **WHEN** downloads are disabled and the model home contains only isnet or u2net weights
- **THEN** the default model is unavailable and the backend fails before importing rembg
  or attempting network access

#### Scenario: The code-only model directory cannot silently relocate the weight
- **WHEN** `ART_REMBG_MODEL_DIR` resolves its effective value
- **THEN** no environment variable is read, so a mistyped variable cannot silently
  relocate the default weight away from the baked image path or a bare-metal cache

#### Scenario: The backend redirects rembg's model home off tmpfs HOME
- **WHEN** the backend prepares rembg
- **THEN** it sets the model-home variables before the lazy import, so the library's
  default location under `$HOME` is never used

#### Scenario: The sole model's licensing responsibility is documented
- **WHEN** the settings comments, `.env.example`, and operator documentation are inspected
- **THEN** they identify `bria-rmbg` as BRIA RMBG-2.0, state its BRIA licensing and
  non-commercial free/commercial-licence distinction, and assign applicable use and
  redistribution licence compliance to the image publisher and operator
- **AND** they advertise no model-selection knob or permissively licensed replacement path

#### Scenario: Downloads disabled verifies the cache before the session
- **WHEN** `ART_REMBG_DOWNLOAD_ENABLED` is false
- **THEN** the backend verifies the default-model artifact under `ART_REMBG_MODEL_DIR`
  before building a session and raises `art_cutout_unavailable` immediately when absent,
  performing no rembg import, network access, or unbounded wait

#### Scenario: A pre-seeded default artifact permits offline bare-metal use
- **WHEN** downloads are disabled and `bria-rmbg.onnx` is present in the model home's
  `models/bria-rmbg/` directory or rembg's supported flat layout
- **THEN** the real backend proceeds to construct the default CPU session without a fetch
- **AND** an unloadable artifact still surfaces the bounded `art_cutout_unavailable` code

#### Scenario: Enabled downloads retain non-container acquisition
- **WHEN** downloads are enabled on a bare-metal or explicitly overridden writable home
  without the default artifact
- **THEN** the existing rembg acquisition path downloads the default artifact into
  that home, and acquisition failures remain `art_cutout_unavailable`

#### Scenario: The standard image needs no runtime acquisition
- **WHEN** the standard image runs its first enabled portrait cutout with runtime model
  network access unavailable, with downloads disabled and separately enabled
- **THEN** the backend reads the baked default weight and performs no model download
- **AND** no startup copy or rembg volume initialization is required
