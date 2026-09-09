## Why

Character and monster portraits are generated as full rectangular scenes: the subject
stands on an invented floor, in front of an invented backdrop, with a ground shadow.
The webclient composes those portraits over its own panel chrome, so every portrait
drags a rectangle of unrelated background across the layout, and no presentation layer
can ever place a character over a room image, a party row, or a combat frame without a
visible seam.

A one-time survey on the project's own hardware settled the feasibility question:
`rembg` with the `bria-rmbg` model runs entirely on CPU (~3.1 s one-time session build,
~9.8 s per 920x1536 image on 24 cores) and produces excellent alpha — fine hair edges
kept, ground shadow removed. The same survey ruled GPU out on the target box: ONNX
Runtime's CUDA execution provider needs `libcudnn.so.9`, `libcublasLt.so.12`,
`libcufft`, `libcurand`, and the `libcudnn_ops`/`libcudnn_adv` set that the host does
not have, and with pip `nvidia-*` wheels forced in, `bria-rmbg` runs out of VRAM beside
the sd-webui process it shares the RTX 3060 with. CPU-only sidesteps all of it and
leaves the GPU entirely to image generation.

Scenes are deliberately excluded. A scene *is* its background; removing it would leave
nothing.

## What Changes

- A new local post-processing stage runs between the sd-webui client's returned PNG
  bytes and `world/art/formats.py::encode(...)`: for character and monster portrait
  subjects only, the bytes are replaced by a transparent-background cutout, and the
  cutout is what gets encoded, written, and published. Scene subjects skip the stage
  entirely and keep their current bytes.
- The stage covers **both** portrait publication paths — the classic per-subject record
  (`portrait/character/<key><ext>`, `portrait/monster/<key><ext>`) and gallery jobs
  (`gallery/<kind-dir>/<subject-key>/<image-id><ext>`) — because both produce the same
  portrait art. The gate is the subject kind, which both record shapes carry.
- The background-removal backend is an injectable seam (`ART_REMBG_BACKEND` dotted
  path, mirroring `ART_SD_CLIENT`) with a CPU-only `rembg` implementation and a
  deterministic in-repo fake, so no test ever loads a 1 GB ONNX model or touches the
  network.
- The stage is off by default (`ART_REMBG_ENABLED=false`) and turned on per deployment.
  See design D2 — it keeps the code defaults, and therefore the test defaults, free of a
  1 GB first-use download and a multi-second CPU pass per image.
- A cutout failure is a bounded per-job failure with two new named codes
  (`art_cutout_unavailable`, `art_cutout_error`), settled exactly like today's
  `sd_format_error`: prior valid output retained, batch-mates unaffected, no job left
  `in_progress`, and `@art retry` recovers once the model or the box is fixed. The
  sd-webui generation itself is never blocked, re-issued, or failed by this stage.
  Because the one-time model download is the first step that can legitimately overrun
  the lease, the classic terminal-failure settle becomes claim-token guarded (design
  D6a) so a stale worker's late failure can never steal a newly claimed record.
- Alpha-hostile configuration is refused at boot rather than silently discarded:
  `ART_REMBG_ENABLED=true` together with `ART_SD_OUTPUT_FORMAT=jpeg` raises
  `ImproperlyConfigured` at settings import, because JPEG's RGB normalization would
  drop the alpha and store a portrait that still has its background while claiming to be
  a cutout.
- The 1 GB model is cached in a code-only, container-persistent directory
  (`server/.rembg`, new volume) instead of `~/.rembg/models` — which under the image's
  `HOME=/tmp` tmpfs would be re-downloaded on every container start.
- `rembg` and CPU-only `onnxruntime` are added to `pyproject.toml`/`uv.lock`.
  `onnxruntime-gpu` is explicitly NOT used; the backend pins `CPUExecutionProvider`.

## Capabilities

### New Capabilities

- `art-portrait-cutout`: the portrait background-removal stage — its subject-kind
  scope, its injectable CPU-only backend seam and cached session, its settings family
  (enable flag, model choice, model cache directory, download policy, lease allowance),
  its bounded failure codes, and its boundary events.

### Modified Capabilities

- `art-queue-worker`: the internal worker contract gains the cutout stage in its
  pipeline order, the two new bounded failure codes, and a lease bound that includes the
  cutout allowance when the stage is enabled.
- `art-output-format-pipeline`: a new requirement that an alpha channel survives the
  three alpha-capable output formats (`png`, `webp`, `avif`) end to end; the existing
  JPEG RGB-normalization requirement is unchanged.
- `settings-environment-overrides`: the exact env-backed inventory gains
  `ART_REMBG_ENABLED`, `ART_REMBG_MODEL`, `ART_REMBG_DOWNLOAD_ENABLED`,
  `ART_REMBG_ALLOWANCE_SECONDS`, and `ART_REMBG_THREADS` with their conversion rules, and
  repairs the inventory's existing omission of `DEFEAT_ADULT_SCENES` (live in
  `settings.py`, `test_settings.py`, and the AST contract test since before this change); the never-environment-
  configurable requirement gains `ART_REMBG_BACKEND` (an import-executing seam) and
  `ART_REMBG_MODEL_DIR` (a persistent-volume path, same rationale as `ART_STORE_ROOT`).
- `container-image`: the image and `compose.yaml` gain the persistent model-cache mount
  at `/app/server/.rembg`.

## Impact

- **New code**: `world/art/cutout.py` (seam, backend, kind scope, bounded errors),
  `world/art/fake_cutout.py` (deterministic double).
- **Modified code**: `world/art/worker.py` (one stage call in `_settle_one`, one
  `except` arm, the lease formula), `world/art/queue.py` (`settle`/`_settle_by_key`
  become claim-token guarded — design D6a), `server/conf/settings.py` (seven settings plus the
  jpeg-vs-alpha boot check), `server/conf/test_settings.py` (`_ENV_OVERRIDES`).
- **Dependencies**: `rembg` + `onnxruntime` (CPU). This is a material image-size
  increase (onnxruntime, numpy, opencv-headless, pymatting, scipy) plus a 1 GB model
  fetched at runtime, not baked into the image.
- **Container**: `Containerfile` (`install -d` + `VOLUME`), `compose.yaml` (named
  volume), `.env.example`.
- **Contract tests that MUST be updated in this change** (each fails otherwise):
  `server/conf/tests/test_env_overrides.py` (AST inventory, `.env.example` coverage,
  `test_settings` override-name parity, settings-guide coverage),
  `docs/development/settings-and-environment.md` and the `ART_SD_*` table in
  `docs/gm/prompts.md`.
  `world/art/tests/test_queue.py` (the token-guarded `settle` signature and its stale-claim
  scenarios). The new `world.art.tests.test_cutout` module is expected to need NO shard-manifest
  edit (shard 4 already owns the `world.art` prefix); the ownership contract test verifies that.
- **Not touched**: `world/ai/` (this is the deterministic art pipeline, single-writer
  boundary unchanged), the sd-webui wire protocol, the store-path confinement rules, the
  media route, the presenter, the wire payloads, and every player-facing command. The two
  new error codes need no consumer change — `last_error_code` is a free-text
  `AttributeProperty` on both the asset record and the `GalleryRecord`, rendered verbatim
  by `commands/art.py`, with no closed set anywhere; `worker_output_out_of_root` is the
  existing non-`sd_`-prefixed precedent.
- **Deliberately out of scope**: seed-synchronized art. `world/art/gallery_seed.py`
  imports operator-supplied PNGs straight into the store without touching the worker, so
  seeded portraits keep their backgrounds and a gallery may legitimately mix cut-out and
  opaque cards. The engine must not silently rewrite files the operator supplied.

## Risks

- **Licensing.** `bria-rmbg` wraps BRIA's RMBG-2.0 weights, which are BRIA-licensed:
  free for non-commercial use, commercial use requires a licence from BRIA. This change
  therefore does not hard-code the model — `ART_REMBG_MODEL` is a closed-choice setting
  whose permissively licensed `isnet-anime` (~176 MB) entry is a drop-in replacement
  requiring only an env change and a requeue. The default stays `bria-rmbg` at the
  project owner's request; the operator owns the licence decision, and the setting
  documentation says so.
- **Image size, first-run download, and supply chain.** The dependency set is heavy and
  the ~1 GB model is fetched at runtime, not baked into the image, then executed as an
  ONNX graph. The engine adds no download URL of its own — the fetch is `rembg`'s, from
  its own pinned location with its own integrity check, with `rembg`/`onnxruntime` pinned
  in `uv.lock`. Mitigated by the default-off flag, the persistent cache volume, and
  `ART_REMBG_DOWNLOAD_ENABLED=false`, which turns a missing model into an immediate
  bounded failure and makes runtime network access for this feature structurally
  impossible for deployments that pre-seed the volume from a trusted machine.
- **Permanent resident memory in the game server.** The inference session is cached for
  the process lifetime, so the Evennia server's RSS grows by roughly 1–1.5 GB after the
  first portrait and never shrinks (an order of magnitude less with `isnet-anime`). On a
  small host this is the difference between running and being OOM-killed. It is sized for
  in the operator documentation rather than discovered; session eviction is a deliberate
  follow-up, not a gap (design: risks).
- **Throughput.** ~10 s of CPU per portrait on 24 cores serializes behind the single
  worker slot and competes with nothing else the engine does synchronously, but a small
  box will be slower. The lease bound is widened accordingly (design D6) and gameplay
  never waits on it.
