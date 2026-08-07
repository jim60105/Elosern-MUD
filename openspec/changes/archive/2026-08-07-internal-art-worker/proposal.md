## Why

Design D11 makes the art pipeline "external": the engine never calls Stable Diffusion — it
maintains a queue and shells out to a configurable worker command (`ART_WORKER_CMD`, default
`tools.art_worker`, a subprocess speaking JSON-lines on stdin/stdout). That boundary was chosen to
keep the engine GPU-free, but it has real costs on this single-machine deployment: the shipped
"worker" is a placeholder stub, a real image generator is a second program to install and debug,
and the full sd-webui prompt lives outside the version-controlled prompt library, so an admin
cannot tune image generation the same way they tune every other prompt. The owner now wants the
worker to be an internal program: the engine calls sd-webui itself through an in-process client,
with the image prompts stored in `prompts/art.yaml` under the externalized-prompt-library design.

## What Changes

- **Replace the external subprocess worker with an internal sd-webui client.** A new
  `world/art/sd_worker.py` (client) builds a `/sdapi/v1/txt2img` request from the prompt library
  and generation settings, calls the configured `SD_WEBUI_BASE_URL` synchronously with a bounded
  timeout, validates the response (JSON envelope, `images[0]` base64 → PNG magic bytes), writes
  the image under the art store root, and settles the queue record. `ART_WORKER_CMD`,
  `tools/art_worker.py`, and the fixture subprocess worker are removed. **BREAKING** — acceptable,
  the project has no released users.
- **Image generation prompts move under the prompt library.** `prompts/art.yaml` gains
  `art.scene_prompt`, `art.portrait_prompt` (templates with a `{description}` placeholder built
  per the image-prompt-builder-nl skill) and `art.negative_prompt`; the client renders them via
  `render_prompt(...)` like every other layer, so admins tune image prompts in the same mounted
  folder as narrator/dialogue prompts.
- **Generation parameters become settings.** `ART_SD_BASE_URL` (from `SD_WEBUI_BASE_URL`),
  `ART_SD_TIMEOUT_SECONDS` (default 600), `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
  `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT` (optional model title), and per-aspect-ratio sizes
  (scene 16:9, portrait 3:4) — mirroring how `LLM_PROFILES` keeps endpoint configuration in
  settings while prompt text lives in the library.
- **Queue machinery is unchanged.** Claim/settle/lease, the single worker concurrency slot, the
  background Twisted thread drain, and the `@art` commands all keep their contracts; only the
  "run the worker" step changes from a subprocess protocol to an in-process client call.
- **Offline playability is preserved.** When sd-webui is unreachable or returns garbage, the
  client resolves to bounded named error codes (`sd_connection_error`, `sd_timeout`,
  `sd_http_error`, `sd_malformed_response`, `sd_no_image`, `sd_decode_error`, `sd_not_png`,
  `sd_response_too_large`, `sd_image_dimensions_too_large`, `sd_prompt_error`,
  `sd_client_config_error`, `sd_internal_error`), records settle `failed`, placeholders remain,
  and the deterministic game stays fully playable.
- **Outputs are written atomically.** PNG bytes go to a unique temporary file in the store
  directory and are moved onto the final identity with an atomic replace, so a failed or
  interrupted regeneration never corrupts the image players see; the record's prior valid output
  is always retained.
- **Resource use is bounded.** The transport enforces a total wall-clock deadline (not just
  socket timeouts), caps response body/base64 size and decoded PNG dimensions, and rejects
  redirects and non-http(s) schemes.
- **Prompt edits are visible.** The queue record stores a rendered-prompt digest alongside the
  description hash; editing an `art.*` prompt on a `done` record sets the existing `hash_changed`
  staff-review flag and never silently replaces the image, and `@art requeue` regenerates.
- **Deterministic testing without a socket.** A `FakeSDWebUIClient` (same philosophy as
  `FakeLLMClient`) replays fixed PNG fixtures and scripted failures; tests and the browser
  harness inject it through the `ART_SD_CLIENT` setting, so no test ever opens a network
  connection.
- **Design-document amendment.** D11 and §8's worker-contract block are amended in the design
  doc: the engine now owns an internal sd-webui client; the swappable seam becomes the prompt
  library plus the client settings, and the worker no longer ships as an external command.

## Capabilities

### New Capabilities
- `internal-art-worker`: The in-process sd-webui client (`world/art/sd_worker.py`), the
  `art.scene_prompt` / `art.portrait_prompt` / `art.negative_prompt` prompt-library keys it
  renders, the `ART_SD_*` generation settings, response validation with resource caps, the
  bounded error taxonomy, atomic store writes, the rendered-prompt digest on queue records, the
  injectable fake client, and the offline degradation contract.

### Modified Capabilities
- `art-queue-worker`: The worker-contract requirement changes from an external subprocess
  protocol to the internal sd-webui client (RENAMED + MODIFIED); the serialization lock, single
  concurrency slot, lease reclaim, scheduler settings, and changed-source-hash reporting stay.

## Impact

- **New code**: `world/art/sd_worker.py`, `world/art/fake_sd_client.py`, `world/art/tests/`
  additions, `prompts/art.yaml` generation keys (authored at apply time with the
  image-prompt-builder-nl skill), `docs/gm/prompts.md` update for the new art keys.
- **Removed**: `ART_WORKER_CMD` and `ART_WORKER_TIMEOUT_SECONDS` settings, `tools/art_worker.py`,
  `world/art/tests/fixtures/fixture_worker.py`, the JSON-lines worker protocol in
  `world/art/worker.py`.
- **Modified**: `server/conf/settings.py`, `web/tests/browser/browser_settings.py`,
  `web/tests/browser/test_browser_art.py`, `tests/test_art_offline_contract.py`,
  `server/conf/tests/test_art_settings.py`, `world/art/worker.py`, `world/art/tests/test_worker.py`,
  `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (D11, §8 amendment).
- **Dependencies**: builds on `externalized-prompt-library` (the `prompts/` folder and
  `world/prompts` registry it introduces). Compose already passes `SD_WEBUI_BASE_URL`; no
  compose change is needed.
- **Out of scope**: progress polling and job cancellation (`/sdapi/v1/progress`,
  `/sdapi/v1/interrupt`), model/sampler enumeration flows, and img2img — the first version is a
  bounded synchronous txt2img call, matching the existing single-slot serialized worker.
