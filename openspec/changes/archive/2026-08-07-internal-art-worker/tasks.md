## 1. Prompt-library integration (depends on externalized-prompt-library being applied)

- [x] 1.1 Confirm the `externalized-prompt-library` change is applied first: `prompts/` exists,
      `world/prompts` provides `render_prompt`, and `prompts/art.yaml` carries the base art keys.
- [x] 1.2 Extend `prompts/art.yaml` with `art.scene_prompt` and `art.portrait_prompt` templates
      (each with a `{description}` placeholder) and `art.negative_prompt` (no placeholders),
      authored with the image-prompt-builder-nl skill's guidance; register the three keys and
      their placeholder allowlists in `world/prompts/registry.py::PROMPT_SPECS`.
- [x] 1.3 Add a prompt-library guarded test proving the three art generation keys load, render
      deterministically, and reject unknown placeholders, and that editing a template changes
      the rendered-prompt digest while the deterministic `description`/source hash is untouched.

## 2. Internal sd-webui client

- [x] 2.1 Implement `world/art/sd_worker.py`: `build_txt2img_request(subject, description)` that
      renders `art.scene_prompt`/`art.portrait_prompt`/`art.negative_prompt` through
      `render_prompt`, applies `ART_SD_*` settings (steps, cfg, sizes by aspect ratio, optional
      sampler/scheduler/checkpoint), and always sets
      `override_settings.samples_format: "png"` with `override_settings_restore_afterwards: true`.
- [x] 2.2 Implement `SDWebUIClient` with an injectable transport callable; the default transport
      POSTs `{ART_SD_BASE_URL}/sdapi/v1/txt2img` via stdlib `urllib.request`, restricts the
      scheme to `http`/`https`, disables redirects, and enforces a **total wall-clock deadline**
      over the whole exchange (chunked reads against a monotonic budget, not just socket
      timeouts); `generate(subject, description) -> bytes` validates the envelope (HTTP 200,
      JSON, non-empty `images`, base64 decodes, PNG magic) and returns the decoded PNG bytes.
- [x] 2.3 Enforce the resource caps: read the response body under `ART_SD_MAX_RESPONSE_BYTES`,
      decode base64 under the same bound, parse the PNG IHDR and reject width/height/pixels
      beyond `ART_SD_MAX_IMAGE_DIMENSIONS`/`ART_SD_MAX_IMAGE_PIXELS` before any unbounded
      allocation.
- [x] 2.4 Define the bounded error taxonomy: `sd_connection_error`, `sd_timeout`,
      `sd_http_error`, `sd_malformed_response`, `sd_no_image`, `sd_decode_error`, `sd_not_png`,
      `sd_response_too_large`, `sd_image_dimensions_too_large`, `sd_prompt_error`,
      `sd_client_config_error`, `sd_internal_error`; every failure mode maps to exactly one named
      `SDError`, and no unexpected exception escapes `generate()`.
- [x] 2.5 Implement the opt-in one-time `samples_format=png` pre-pin via
      `POST /sdapi/v1/options` behind `ART_SD_PREPIN_SAMPLES_FORMAT = False` by default; when
      enabled it runs once per process under a lock-protected guard, logs when it mutates the
      server, and never fails a job on its own failure.
- [x] 2.6 Add the `ART_SD_*` settings (base URL, timeout 600, steps, cfg, sampler, scheduler,
      checkpoint, scene/portrait sizes, client dotted path, response/IHDR caps, pre-pin flag) to
      `server/conf/settings.py`; remove `ART_WORKER_CMD` and `ART_WORKER_TIMEOUT_SECONDS`.
- [x] 2.7 Implement `world/art/fake_sd_client.py::FakeSDWebUIClient` with the same interface:
      replays a fixed valid PNG fixture, scripts each named `SDError`, records the requests it
      received, and never opens a socket.

## 3. Worker integration

- [x] 3.1 Rewrite `world/art/worker.py` to replace the subprocess/JSON-lines protocol with the
      internal client: per claimed record, resolve the client via `settings.ART_SD_CLIENT`, call
      `generate(subject, description)`, write the returned bytes to `expected_output_identity`
      under the store root (keeping the symlink-resolved under-root check), and settle `done`.
- [x] 3.2 Implement the atomic output write: write to a unique temporary file inside the store
      directory, flush, then `os.replace()` onto the final identity; on any failure remove the
      temporary file and never touch the existing output or the record's prior valid output.
- [x] 3.3 Map every named `SDError`, plus prompt-render (`sd_prompt_error`), client-resolution
      (`sd_client_config_error`), and unexpected (`sd_internal_error`) failures, to a per-subject
      `failed` settle so every claimed job reaches a terminal state; keep the single worker
      concurrency slot and `drain()`/`drain_synchronous()` on the background thread.
- [x] 3.4 Size lease reclaim by the worst-case batch (`claimed_batch_size ×
      ART_SD_TIMEOUT_SECONDS + margin`) instead of a flat timeout; keep
      `_notify_completed_batch`.
- [x] 3.5 Remove `tools/art_worker.py`, `world/art/tests/fixtures/fixture_worker.py`, and the
      `_worker_env()`/`_build_job()`/`_valid_result()` subprocess machinery; update
      `commands/art.py` error handling from the subprocess `OSError` path to the named-client
      error path.
- [x] 3.6 Extend `world/art/queue.py::ensure()` and the store record with a rendered-prompt
      digest (sha256 of the rendered positive/negative prompt pair) alongside `source_hash`;
      either changing on a `done` record sets `hash_changed` and never silently replaces the
      image; `@art requeue` regenerates with prior-output retention.
- [x] 3.7 Add `server/conf/tests/test_art_settings.py` assertions for every `ART_SD_*` setting
      and drop the `tools/art_worker.py`-exists check.

## 4. Offline and browser harness

- [x] 4.1 Update `tests/test_art_offline_contract.py`: point `ART_SD_CLIENT` at the fake with a
      scripted failure (or an unreachable base URL via a short timeout) and keep the
      repository-wide acceptance — LLM and image services offline, deterministic game fully
      playable, every art record degrades to placeholders.
- [x] 4.2 Update `web/tests/browser/browser_settings.py` to replace `ELOSERN_BROWSER_ART_WORKER_CMD`
      with `ELOSERN_BROWSER_SD_CLIENT` (a fake dotted path) and set the `ART_SD_*` defaults the
      harness needs; update `web/tests/browser/test_browser_art.py` env wiring.
- [x] 4.3 Rewrite `world/art/tests/test_worker.py` to exercise the internal contract via
      `FakeSDWebUIClient`: success writes the expected identity atomically; each scripted
      `SDError` settles the matching bounded code; prompt/client/internal errors settle
      `sd_prompt_error`/`sd_client_config_error`/`sd_internal_error`; out-of-root rejection; a
      failed regeneration leaves the prior image intact; a slow batch is not reclaimed before
      `N × timeout + margin`; no job left `in_progress`; the single concurrency slot behavior
      stays covered. Re-annotate tests whose requirement IDs changed with the renamed
      `art-queue-worker` requirement ID and the new `internal-art-worker::*` IDs.
- [x] 4.4 Update `world/art/tests/test_presenter.py` to inject `FakeSDWebUIClient` instead of the
      removed `ART_WORKER_CMD` seam and assert "no generation requested" via the fake's call
      records; add `world/art/tests/test_queue.py` (or extend existing) coverage for the
      rendered-prompt digest `hash_changed` flag.

## 5. Docs and design-document amendment

- [x] 5.1 Update `docs/gm/prompts.md` with the three new `art.*` generation prompt keys, the
      `{description}` placeholder rule, the `ART_SD_*` generation settings table (including the
      response/IHDR caps and the opt-in `ART_SD_PREPIN_SAMPLES_FORMAT` pre-pin with its server
      side effect), and the prompt-edit workflow (edit → validate → restart → review the
      `hash_changed` flag → `@art requeue` to regenerate).
- [x] 5.2 Amend `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`: add the "Amended
      (change internal-art-worker)" note to D11 and §8 stating the worker is now an internal
      sd-webui client, the swappable seam is the prompt library plus `ART_SD_*` settings, and the
      external `ART_WORKER_CMD` contract is removed; update the §11 roadmap wording for change 22
      to reference the internal worker.

## 6. Verification

- [x] 6.1 Run `openspec validate internal-art-worker --strict` and
      `uv run --locked python -m tools.spec_traceability check`.
- [x] 6.2 Run the affected suites until green: `world.art`, `server.conf.tests.test_art_settings`,
      `tests/test_art_offline_contract.py`, `tests/`, and the browser art tests
      (`uv run --locked python -m unittest discover -s web/tests/browser -t .` for the art file).
- [x] 6.3 Run `uv run --locked python -m compileall -q world typeclasses commands server` and
      `git diff --check`; grep to confirm no module references `ART_WORKER_CMD`, `tools.art_worker`,
      or the removed fixture worker, and that no test opens a socket to an image service.
