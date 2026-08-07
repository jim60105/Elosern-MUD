## Context

Design D11 draws the line "the engine never calls Stable Diffusion; it shells out to a
configurable worker command". Today that boundary is `ART_WORKER_CMD` (default
`[sys.executable, "-m", "tools.art_worker"]`): `world/art/worker.py` builds JSON-lines jobs
`{kind, key, description, out_path, aspect_ratio}`, spawns the subprocess with a bounded timeout,
and validates the JSON-lines results one-to-one (key match, status, exact output identity,
store-root confinement). The shipped default worker writes a deterministic 1×1 transparent PNG so
the pipeline is verifiable offline; the test suite has a fixture subprocess worker with scripted
failure modes.

The owner's deployment is a single machine whose sd-webui is reached at `SD_WEBUI_BASE_URL`
(compose already sets `http://host.containers.internal:7860`). The external boundary adds a
second program to install and debug, and the full sd-webui prompt never enters the versioned
prompt library. The `externalized-prompt-library` change (in progress) will provide the
`prompts/` folder and the `world/prompts` registry; this change builds on it so image prompts
live in `prompts/art.yaml` like every other prompt.

## Goals / Non-Goals

**Goals:**
- Replace the external subprocess worker with an internal, in-process sd-webui client that POSTs
  `/sdapi/v1/txt2img` with a bounded timeout and writes the returned PNG under the art store root.
- Keep the queue machinery intact: claim/settle, lease reclaim, the single worker concurrency
  slot, the background Twisted thread drain, and the `@art` commands.
- Keep the deterministic game fully playable offline: an unreachable or misbehaving sd-webui
  settles records `failed` with bounded named error codes; placeholders remain.
- Store the image-generation prompts (`art.scene_prompt`, `art.portrait_prompt`,
  `art.negative_prompt`) in `prompts/art.yaml`, rendered through the prompt library like every
  other layer; author the prompt text at apply time with the image-prompt-builder-nl skill.
- Keep every test deterministic and socket-free via an injectable fake sd-webui client.
- Explicitly amend design D11 and §8 in the design document.

**Non-Goals:**
- No progress polling (`/sdapi/v1/progress`), no cancellation (`/sdapi/v1/interrupt`/`skip`), no
  model/sampler enumeration flows, no img2img — the first version is a bounded synchronous
  txt2img call that matches the existing single-slot serialized worker.
- No backward compatibility for `ART_WORKER_CMD`, `tools/art_worker.py`, or the JSON-lines
  protocol: the project has no released users.
- No change to the art subject model, descriptions, source hashing, presenters, or the
  webclient art panel.

## Decisions

### D-1: In-process client in `world/art/sd_worker.py`, injected transport for tests

A new `world/art/sd_worker.py` owns everything the subprocess used to do:

- `build_txt2img_request(subject, description) -> dict` — renders the positive prompt from
  `art.scene_prompt` (scenes) or `art.portrait_prompt` (portraits) with the deterministic
  `description` substituted, renders `art.negative_prompt`, and fills `steps`, `cfg_scale`,
  `width`/`height` (from the aspect ratio via settings), `sampler_name`, `scheduler`,
  `override_settings.samples_format: "png"`, and `override_settings_restore_afterwards: true`.
  An optional `ART_SD_CHECKPOINT` becomes `override_settings.sd_model_checkpoint` (server default
  when empty).
- `SDWebUIClient` — `generate(subject, description) -> bytes`: POSTs the request to
  `{ART_SD_BASE_URL}/sdapi/v1/txt2img`, validates the response, and returns the decoded PNG
  bytes. The HTTP call is a synchronous stdlib `http.client` exchange with a bounded timeout; it
  runs on the background Twisted worker thread (never the reactor thread), exactly like the
  subprocess call it replaces, so no new dependency and no event-loop blocking.
- **Hard wall-clock deadline per request.** The connection is opened with a socket timeout
  bounded by the remaining budget, every body chunk read is bounded by the budget still left at
  that moment (the socket timeout is refreshed before each read against a monotonic clock), and
  the connection is closed when the budget is exhausted; the violation maps to `sd_timeout`.
  DNS resolution is the one step stdlib cannot bound from this thread — it is bounded by the
  OS resolver, like any other stdlib client.
- **Response resource caps.** The client rejects oversized responses before allocating
  unbounded memory: the HTTP body read is capped at `ART_SD_MAX_RESPONSE_BYTES` (default 50 MiB),
  the base64 payload is capped at the same bound, and the decoded PNG must parse a genuine IHDR
  (chunk type and length verified) whose width, height, and width×height stay within
  `ART_SD_MAX_IMAGE_DIMENSIONS` (default 4096) and `ART_SD_MAX_IMAGE_PIXELS` (default 16 MiB).
  Violations map to `sd_response_too_large` and `sd_image_dimensions_too_large`.
- **Scheme and redirect policy.** The base URL is trusted deployment configuration, but the
  default transport still restricts the scheme to `http`/`https` and never follows redirects
  (`http.client` has no redirect logic, so a 3xx is a bounded `sd_http_error`), so an odd
  setting cannot probe internal services or silently change targets.
- A transport seam: the client accepts an injectable transport callable
  (`transport(request) -> dict`), defaulting to the real `urllib` POST. Tests and the browser
  harness inject `FakeSDWebUIClient` through the `ART_SD_CLIENT` dotted-path setting, mirroring
  `FakeLLMClient` — deterministic PNG fixtures and scripted failures, never a socket.

The client maps every failure mode to a named `SDError` code: `sd_connection_error`,
`sd_timeout`, `sd_http_error`, `sd_malformed_response`, `sd_no_image`, `sd_decode_error`,
`sd_not_png`, `sd_response_too_large`, `sd_image_dimensions_too_large`. `world/art/worker.py`
catches these per subject and settles `failed` with the bounded code; the offline degrade path is
unchanged in spirit (records failed → placeholders → game playable).

**Every claimed subject reaches a terminal settle.** Prompt-template render failures, an
`ART_SD_CLIENT` dotted-path that cannot be resolved or constructed, and unexpected client bugs
are not `SDError`s, so the worker wraps the whole per-subject pipeline (render → resolve client →
generate → write) and maps those to additional bounded codes `sd_prompt_error`,
`sd_client_config_error`, and `sd_internal_error`. A batch can therefore never be left half
`in_progress` by a bad admin prompt or a settings typo: the bad subject settles `failed` with the
named code and the rest of the batch proceeds.

Alternative considered: keep the subprocess but vendor a real worker script. Rejected — the
owner explicitly wants an internal program, and an in-process client removes the second process,
the JSON-lines protocol, and the env plumbing while keeping the single-slot serialization.

### D-2: Prompt construction goes through the prompt library

`world/art/sd_worker.py` reads its prompt text exclusively from `world/prompts`:

- `art.scene_prompt` — positive prompt template for scene subjects, `{description}` placeholder.
- `art.portrait_prompt` — positive prompt template for character/monster portraits, `{description}`
  placeholder.
- `art.negative_prompt` — shared negative prompt, no placeholders.

The `{description}` value is the existing deterministic subject description (scene sentence,
character/monster template) — the same value `world/art/subjects.py` produces today and hashes
for the source hash. The template text itself is authored at apply time with the
image-prompt-builder-nl skill and shipped verbatim in `prompts/art.yaml`, so admins tune image
prompts in the same mounted folder as every other prompt; unknown placeholder tokens are
load-time errors via the prompt library's existing validation.

### D-3: Response validation, atomic output writes, and store-root confinement

The client validates the sd-webui envelope: HTTP 200, body parses as JSON, `images` is a
non-empty list, `images[0]` is base64 and decodes, and the decoded bytes start with the PNG
magic `\x89PNG\r\n\x1a\n` with an IHDR whose dimensions respect the resource caps (D-1). Any
violation raises the matching named `SDError`. The worker writes the bytes to
`expected_output_identity(subject)` (the pre-computed `scene/<key>.png` or
`portrait/.../key.png` under `ART_STORE_ROOT`) and keeps the existing symlink-resolved
under-root check before writing, so a malicious or buggy response can never escape the store
root.

**Atomic replacement preserves the prior valid output.** A regeneration failure must never
corrupt the image players see. The worker writes the PNG to a unique temporary file inside the
same store directory, flushes it, and then `os.replace()`s it onto the final identity; on any
failure the temporary file is removed and the existing output — and the record's
`prior_output_identity` — is never touched. A partially written or crashed generation therefore
leaves the previous valid image intact.

**Stale generations can never publish.** Each claim stores a fresh `generation_token` on the
record; the token-validated `settle_generated()` publishes the temporary file onto the identity
and settles the record `done` in a single critical section under the queue lock, so a worker
whose job was requeued or reclaimed mid-flight (its token no longer matches) can never replace
the record's prior valid output.

### D-3b: Prompt edits are surfaced through the record digest, never silently applied

`source_hash` is defined over the deterministic description only, so editing
`art.scene_prompt`/`art.portrait_prompt`/`art.negative_prompt` would otherwise change the
rendered prompt while leaving the stored hash untouched — silently drifting images away from the
current prompt library. The queue record therefore stores a second digest: the sha256 of the
rendered positive+negative prompt pair for that subject, computed at enqueue time. `ensure()`
compares both the description hash and the prompt digest against the stored values; either
changing on a `done` record sets the existing `hash_changed` staff-review flag and never
silently replaces the completed image. Staff regenerate through the existing `@art requeue`
flow, which also preserves the prior valid output. This keeps the
changed-hash-reported-never-silently-applied invariant true for both inputs of generation.

### D-4: `samples_format` handled request-scoped; pre-pin is opt-in

The sd-webui skill notes that Forge validates `samples_format` *before* applying
`override_settings`, so a server whose persistent value is unsupported (e.g. `avif`) fails even
with the request-scoped override. The client therefore:

1. Sends `override_settings: {"samples_format": "png"}` with
   `override_settings_restore_afterwards: true` on every request (request-scoped, no server
   mutation).
2. Optionally pre-pins `samples_format=png` via `POST /sdapi/v1/options` **only when the
   deployment opts in** with `ART_SD_PREPIN_SAMPLES_FORMAT = True` — the pre-pin permanently
   mutates the shared server's persistent default, so it defaults to `False` and is meant only
   for a dedicated sd-webui instance. When enabled, the pre-pin runs once per process under a
   lock-protected guard, logs when it actually mutates the server, and never fails a job on its
   own failure.

### D-5: Settings replace `ART_WORKER_CMD`

`server/conf/settings.py` removes `ART_WORKER_CMD` and `ART_WORKER_TIMEOUT_SECONDS` and adds:

- `ART_SD_BASE_URL` — from `SD_WEBUI_BASE_URL` env, default `http://127.0.0.1:7860`.
- `ART_SD_TIMEOUT_SECONDS = 600` (sd-webui generation is slow; the skill's curl default).
- `ART_SD_STEPS = 30`, `ART_SD_CFG_SCALE = 7.0`.
- `ART_SD_SAMPLER = ""`, `ART_SD_SCHEDULER = ""` — empty means the server's default; when set,
  the values pass through as `sampler_name`/`scheduler` (admin must match the server's
  enumeration).
- `ART_SD_CHECKPOINT = ""` — optional exact model title; empty means the server's active model.
- `ART_SD_SCENE_WIDTH/HEIGHT = 1344/768` and `ART_SD_PORTRAIT_WIDTH/HEIGHT = 768/1024` —
  multiples of 8, SDXL-friendly, mapped from the record's aspect ratio.
- `ART_SD_CLIENT = "world.art.sd_worker.SDWebUIClient"` — dotted path of the client class;
  tests and the browser harness point this at the fake.
- `ART_SD_MAX_RESPONSE_BYTES = 52428800` (50 MiB), `ART_SD_MAX_IMAGE_DIMENSIONS = 4096`,
  `ART_SD_MAX_IMAGE_PIXELS = 16777216` (16 MiP) — the D-1 resource caps.
- `ART_SD_PREPIN_SAMPLES_FORMAT = False` — opt-in one-time pre-pin (D-4).

**Lease bounds match the worst case.** A batch of up to `ART_SCHEDULER_LIMIT` claimed records
can run for `N × ART_SD_TIMEOUT_SECONDS` on the single slot. Lease reclaim therefore uses
`claimed_batch_size × ART_SD_TIMEOUT_SECONDS + margin` (not a flat timeout), so a slow batch is
never reclaimed while its worker thread is still legitimately running, and the hard per-request
deadline (D-1) plus the per-subject terminal-settle guarantee (D-1) mean a batch always finishes
within a bounded wall-clock budget. `commands/art.py` keeps its drain/retry/requeue/status
contract; the `OSError`-on-subprocess path becomes a named-error path (see D-1).

### D-6: Offline and test contracts

- `tests/test_art_offline_contract.py` updates its wording and one assertion from "worker
  command fixed to fail" to "sd-webui transport fixed to fail" (the fake client injected via
  `ART_SD_CLIENT`), keeping the repository-wide acceptance: LLM and image services offline, the
  deterministic game remains fully playable and every art record degrades to placeholders.
- `web/tests/browser/browser_settings.py` replaces `ELOSERN_BROWSER_ART_WORKER_CMD` with
  `ELOSERN_BROWSER_SD_CLIENT` (a fake dotted path) so the browser harness generates deterministic
  images without a socket; `test_browser_art.py` env wiring is updated accordingly.
- `server/conf/tests/test_art_settings.py` asserts the new `ART_SD_*` settings and drops the
  `tools/art_worker.py`-exists check.

### D-7: Design-document amendment (this change)

D11's "shells out to a configurable worker command" is amended: the engine now owns an internal
sd-webui client; the swappable seam becomes the prompt library plus the `ART_SD_*` settings, and
the worker no longer ships as an external command. §8's worker-contract block (the
`ART_WORKER_CMD` stdin/stdout contract) is amended to the internal txt2img client contract with
its bounded error taxonomy. The design doc's "Amended" notes and the roadmap's change-22 wording
are updated during implementation.

## Risks / Trade-offs

- **A long txt2img call ties the single worker slot** → bounded by the per-request hard
  wall-clock deadline (`ART_SD_TIMEOUT_SECONDS`), lease reclaim sized to the worst-case batch
  (`N × timeout + margin`), and per-subject terminal settles; the reactor thread never blocks,
  and the queue is serialized by design.
- **sd-webui unavailable or misconfigured** → bounded named error codes settle `failed`;
  placeholders remain; the deterministic game is untouched (existing offline invariant).
- **Model/sampler names must match the server's enumeration** → empty defaults mean "server
  default"; an admin who sets them and gets it wrong sees a bounded `sd_http_error` code, and the
  `@art status`/`@art retry` flow recovers.
- **Prompt text edits versus the description hash** → the queue stores both the description
  hash and a rendered-prompt digest; either changing on a `done` record surfaces the existing
  `hash_changed` staff-review flag and never silently replaces the image, and `@art requeue`
  regenerates with prior-output retention.
- **`samples_format` pre-pin mutates the shared server's persistent default** → the pre-pin is
  opt-in (`ART_SD_PREPIN_SAMPLES_FORMAT = False` by default) and one-time per process under a
  lock guard; the request-scoped override is the primary mechanism.
- **Oversized or malformed responses** → capped reads, base64/decode bounds, and PNG IHDR
  dimension/pixel limits map to `sd_response_too_large` / `sd_image_dimensions_too_large`
  bounded failures instead of unbounded memory use.
- **Removing the subprocess worker breaks the offline placeholder PNG behavior** → placeholders
  were a verification aid; real offline behavior is the presenter's truthful placeholder for
  failed/missing records, which is unchanged and now exercised by the fake-client offline test.
