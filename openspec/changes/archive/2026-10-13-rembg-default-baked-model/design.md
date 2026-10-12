# Design

## Context

See [proposal.md](proposal.md) for motivation and scope. The current backend chooses a model from `settings.ART_REMBG_MODEL`, caches sessions in a model-keyed dictionary, sets both `U2NET_HOME` and `REMBG_HOME`, and checks for a cached artifact before the lazy rembg import when downloads are disabled. `worker.py` reads the same setting for both cutout boundary events.

`uv.lock` currently locks rembg 2.0.84. Its installed `session_factory.py` declares `new_session(model_name="bria-rmbg", ...)`. `BriaRmBgSession.download_models()` downloads RMBG-2.0 using an upstream SHA-256, saves `models/bria-rmbg/bria-rmbg.onnx` under the configured home, and reuses a present file without a fetch. Calling that class method acquires the artifact without constructing an ONNX inference session. Existing source comments mentioning 2.0.69 are stale where they describe this changed path.

The image currently prepares an empty `root:0`, mode-0775 `/app/server/.rembg`, declares it as a `VOLUME`, and Compose mounts `evennia-rembg` there. A named volume copies image content only on first creation; an existing volume hides later image contents. The current `container-image` spec additionally forbids baking the model, and architecture design §9 limits runtime contents to the virtual environment and application code. Both contracts require an explicit amendment for this request.

Settings tests have moved to `server/conf/tests/test_art_settings.py` and `server/conf/tests/test_env_overrides/`. The environment spec still names the model knob in its exact inventory and coercion scenarios. These are part of the cutover, alongside `world/art/tests/test_cutout.py` and `tests/test_container_contract.py`.

## Goals / Non-Goals

**Goals:** The locked dependency's default supplies the sole inference model. The same artifact layout serves the built image and download-disabled bare-metal installations. Container recreation never depends on rembg volume initialization, runtime copying, or downloading. Preserve lazy imports, one-session reuse under the existing lock, CPU-only inference, and bounded failure settlement.

**Non-Goals:** No additional model parameter, backend seam, build argument, downloader abstraction, retry policy, model migration, dependency upgrade, translation-model packaging, or change to player commands. `ART_REMBG_ENABLED`, allowance, thread cap, backend injection, and JPEG guard remain as they are. The retained runtime download switch is not a model-choice parameter.

## Decisions

### D1. Omit the model argument and remove the setting

Remove the `ART_REMBG_MODEL` assignment, environment read, choice validation, bootstrap sanitation entry, and test inventories. Use `new_session(providers=["CPUExecutionProvider"])` in the lazy real backend. Do not substitute a hard-coded model argument or add a replacement operator knob.

Use one nullable module-level session under the existing check-lock-recheck pattern. Remove the model-keyed dictionary and the internal `_build_session(model)` parameter because only one model exists. Keep imports lazy and inference outside the construction lock. Update isolation helpers to save and restore this single session.

A code-only identity such as `REMBG_MODEL_NAME = "bria-rmbg"` in `cutout.py` can name the artifact in readiness checks, errors, and `worker.py` event context. It is metadata, never an argument to `new_session` or an override surface. Keep the `model` event key to preserve the observable event schema. Tests must prove that the session factory receives no positional model or `model_name` keyword and that the locked default is `bria-rmbg`; a lock update changing the default must require a deliberate revision of this contract.

### D2. Download through the locked package before application copying

Add a model-fetch `RUN` in the existing `builder` stage after `uv sync --locked --no-dev --no-install-project`. Set both model-home variables to a dedicated build output such as `/rembg`, then invoke `/venv/bin/python` with `BriaRmBgSession.download_models()` and no model-selection argument. Keep upstream checksum verification enabled. Require a nonempty canonical artifact before exporting the build output; any download/checksum/missing-output failure fails the build. No inference session is built during image construction.

Copy `/rembg/` from the builder to `/app/server/.rembg/` in `app-layout` before its permission normalization, preserving the current stage names and final linked-copy conventions. The model output must be a normal image-stage filesystem output, never solely a Buildah cache mount. The locked fetch precedes application-source copying so ordinary code-only rebuilds can reuse its layer. Use the package's download metadata rather than maintaining a second URL/hash table. The final image carries the weight once, excludes uv caches and acquisition scaffolding, and contains no isnet or u2net weights.

The required image payload grows by approximately 1.02 GB uncompressed. Amend architecture design §9 to identify the background-removal weight as a deliberate runtime-data exception and qualify the previous small-image statement. Keep the multi-stage, CPU-only, non-root, and arbitrary-UID design.

### D3. Remove the rembg volume instead of initializing it

Remove `/app/server/.rembg` from the image's `VOLUME` declaration, remove `evennia-rembg:/app/server/.rembg` from Compose, and remove the rembg-only top-level volume declaration. Preserve database, logs, static/media, art, and translation volume definitions and mounts.

The baked model directory uses `root:0`, directories mode 0755 and files mode 0644. It needs read and traversal permission for the default UID and arbitrary UID with GID 0. Runtime must not require permission to rewrite the weight or copy it into a second cache. The existing directory creation can remain idempotent when the directory already exists; inference reads the artifact from the baked path. This avoids both volume masking and an avoidable 1 GB startup copy.

Retaining the volume and trusting its initial seeding was rejected because old volumes would still hide the artifact. A second baked path plus startup seeding/fallback was rejected because it adds copying and cache-selection behavior. Removing the rembg mount is a clean pre-release cutover. Existing host rembg volumes are left untouched and unused; no command deletes or migrates them. A custom Compose override that mounts this path assumes responsibility for supplying the default artifact.

### D4. Preserve the download switch for nonstandard installations

Keep `ART_REMBG_MODEL_DIR = <GAME_DIR>/server/.rembg`, with its existing `secret_settings.py` override and no environment reader. Keep the typed boolean `ART_REMBG_DOWNLOAD_ENABLED`, default `True`. A standard image already has the model and performs no fetch on first use with either value. Runtime `True` retains existing acquisition behavior only for a bare-metal or explicitly overridden writable directory lacking the artifact. Runtime `False` retains the pre-import, no-network `art_cutout_unavailable` failure for absence.

Retain the existing default-model artifact checks for rembg's canonical nested layout and its upstream-supported flat layout, both for `bria-rmbg` only. This introduces no project compatibility layer or migration. A cache containing only an ISNet/U2Net artifact cannot satisfy readiness for the default model. The image always downloads during its build regardless of `.env`, `ART_REMBG_ENABLED`, or `ART_REMBG_DOWNLOAD_ENABLED`; those values govern the running game, not image construction.

For air-gapped containers, build or obtain the complete image on a connected machine and transfer it before deployment, then set downloads to `False`. No rembg volume pre-seeding is required. For air-gapped bare-metal/custom mounts, obtain the default artifact on a trusted machine and copy it to `<ART_REMBG_MODEL_DIR>/models/bria-rmbg/bria-rmbg.onnx` before disabling downloads. Missing or unloadable artifacts still yield the existing bounded failure codes; no fallback to another model or opaque portrait is permitted.

### D5. Update the complete configuration and evidence surface

Update `.env.example`, the rembg and related comparison text in `docs/development/settings-and-environment.md` and `docs/gm/prompts.md`, and settings/backend comments. Remove model-choice examples and the ISNet permissive-licence escape hatch. Describe BRIA RMBG-2.0 as the sole weight, free for non-commercial use under its licence and requiring appropriate BRIA rights for commercial use; publishers and operators are responsible for applicable use and redistribution permissions. Building an image does not grant those rights. Keep portrait CPU/resident-memory cautions and state the unconditional build-time payload even when cutouts are disabled.

Preserve unaffected requirement names and every unrelated scenario. The installed OpenSpec CLI rejects omitted or renamed scenarios in `MODIFIED` blocks. Explicitly remove and replace the old composite model-choice/cache requirement and the old Compose/rembg-volume requirement, because their model-choice and never-baked scenarios are intentionally retired. The replacement blocks retain all unrelated behavior, and their removal entries name the traceability cutover. Update the four cache-policy decorators in `world/art/tests/test_cutout.py` and six Compose decorators in `tests/test_container_contract.py` to the replacement IDs below. This is a specification/test-annotation cutover, with no runtime migration.

Update the remaining full modified blocks and conflicting translation comparisons. Add build-time model-delivery coverage to `tests/test_container_contract.py`; source-level checks prove the wiring, while a separate manual built-image smoke proves real artifact availability. Do not move test modules or change shard ownership unless a module is actually added, moved, or renamed. The proposal edits only change artifacts. During apply, sync the reviewed deltas into main specs before changing annotation IDs and running traceability gates, because `tools.spec_traceability` reads only `openspec/specs/`, not active deltas. Use the normal sync skill; do not archive unfinished work.

`tools/regenerate_default_art.py` is a supported `ART_REMBG_MODEL` caller and is cut over with the setting: it drops its `--allow-bria` pin and `override_settings(ART_REMBG_MODEL=...)`, takes the sole model identity from `world.art.cutout`, and states in its docstring that a new run publishes BRIA-licensed pixels. Because that removes the permissive production path the committed fallbacks' contract assumed, the change carries a FOURTH delta: `art-gallery-fallback`'s transparent-background requirement keeps its ID and every unrelated scenario, records that the six committed images were produced with the permissive `isnet-anime` model before this cutover (so they carry no BRIA obligation) and pins a future regeneration to the sole shipped weight under the publisher's licence responsibility. The committed images themselves are never regenerated by this change, and no new capability is introduced.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| BRIA licence does not match a deployment or image-distribution use | State the sole-model licence and publisher/operator responsibility; do not claim that rembg's code licence covers the weight. |
| Larger images and builds requiring network/model-host availability | Document the approximately 1.02 GB payload; fetch in a reusable locked-dependency layer and fail the build on acquisition failure. |
| A lock bump changes the default or layout | Add a lightweight default-signature/layout contract without constructing a real session in the automated suite. |
| Custom mounts hide the baked path | Standard Compose declares no rembg mount; document that custom mounts must supply the default weight and keep download-disabled missing-artifact tests. |
| Static container tests miss final-layer contents or permissions | During apply, inspect the built artifact and run a network-disabled image smoke as both the default user and `1000630000:0`. |
| Real inference needs substantial memory and CPU | Build downloads without session creation; retain lazy runtime loading and the existing operator resource warnings. |

## Deployment / Rollback

Build the revised image with `podman compose build`, including the model acquisition, then recreate the service using the revised Compose file. On an air-gapped runtime host, transfer the built image rather than attempting an offline cold build. Old rembg named volumes remain unused; generated portraits and all unrelated persistent data remain unchanged. No data migration or automatic regeneration is required. Rollback consists of selecting the previous image and its matching previous Compose configuration; this change adds no rollback machinery.

## Acceptance and traceability

Extend existing automated tests with patched rembg factories/download boundaries and synthetic bytes only. Cover absent setting, inert former environment values, no model argument, one-session reuse including contention, default-only readiness checks, fixed event context, build-time acquisition wiring, non-root readable permissions, and absence of both named and anonymous rembg volume declarations. Keep the ordinary suite free of model loads and downloads.

Use these retained and replacement literal requirement IDs in substantive tests:

- `art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam`
- `art-portrait-cutout::the-default-removal-model-has-a-code-only-home-and-an-explicit-runtime-download-policy`
- `art-portrait-cutout::the-background-removal-stage-emits-boundary-events`
- `settings-environment-overrides::deployment-settings-accept-typed-environment-overrides`
- `settings-environment-overrides::the-client-seam-and-art-store-root-are-never-environment-configurable`
- `settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact`
- `container-image::multi-stage-containerfile`
- `container-image::compose-persists-mutable-state-and-exposes-image-data`

Run only the six affected test modules explicitly selected in tasks.md. Do not run repository-wide Evennia, unittest, browser, coverage, or CI suites. Integration gates select only static traceability, observability, and manifest checks; do not select the contract gate's unrelated unittest target.

The added model-delivery requirement uses `container-image::the-default-background-removal-model-is-acquired-during-image-build`. Keep `container-image::non-root-arbitrary-uid-capable-runtime` on permission coverage. Manual image acceptance is separate from the automated suite: inspect the final image's nonempty artifact and hash, then perform one real cutout with no network and a read-only root filesystem, output in `/tmp`, using the default UID and separately `1000630000:0`. Use the baked model with downloads disabled and confirm CPU-only initialization and alpha output; no runtime artifact writes or downloads are allowed. Repeat the default readiness path with downloads enabled to prove cached reuse. Capture build and smoke evidence without claiming the source-only tests exercised real weights.
