# Proposal

## Why

Portrait cutouts should use rembg's default `bria-rmbg` model without a model-selection setting. Shipping that weight in the container image makes the first enabled cutout independent of a runtime download.

## What Changes

- **BREAKING** Remove `ART_REMBG_MODEL`, its closed choice set, environment reader, validation, test inventory, and operator configuration examples. The real backend calls `new_session(providers=["CPUExecutionProvider"])` without a model argument and reuses one process-local session.
- Download rembg's default BRIA RMBG-2.0 artifact during the locked-dependency container build, retain checksum verification, and ship it at `/app/server/.rembg/models/bria-rmbg/bria-rmbg.onnx` with arbitrary-UID-readable permissions. A failed fetch fails the build.
- **BREAKING** Remove the rembg-only `VOLUME` entry and `evennia-rembg` Compose mount/declaration so existing or empty named volumes cannot hide the baked artifact. Other persistent mounts remain unchanged; no startup copying or volume migration is introduced.
- Keep `ART_REMBG_MODEL_DIR` code-only and keep `ART_REMBG_DOWNLOAD_ENABLED=True` as the existing non-container/custom-directory acquisition policy. With downloads disabled, a missing default artifact still fails before importing rembg. The standard image needs no first-use model download with either switch value.
- Preserve the model field in cutout boundary events as the fixed `bria-rmbg` identity. Update licensing and deployment documentation to describe the sole BRIA-licensed weight, the approximately 1.02 GB image payload, offline image use, and bare-metal pre-seeding.

## Capabilities

### New Capabilities

None. The behavior belongs to existing portrait, container, and settings capabilities.

### Modified Capabilities

- `art-portrait-cutout`: Use the default model without selection parameters; reuse a single CPU session, retain download-disabled readiness checks, and report the fixed model identity.
- `container-image`: Acquire and ship the default weight during image construction; remove the writable rembg volume while preserving other mounts and non-root operation.
- `settings-environment-overrides`: Remove the model knob from the exact environment inventory, defaults, coercion cases, and operator guide; retain the remaining knobs and code-only seams.

The deltas explicitly remove and replace the two composite contracts containing retired model-choice and never-baked-volume scenarios. The CLI forbids omitting scenarios from `MODIFIED` blocks. Unrelated behavior is preserved in full, and apply updates the affected literal requirement annotations.

## Impact

Implementation touches `server/conf/settings.py`, `server/conf/test_settings.py`, `world/art/cutout.py`, `world/art/worker.py`, `Containerfile`, `compose.yaml`, and their existing tests. Settings regressions now live under `server/conf/tests/`, including `test_art_settings.py` and `test_env_overrides/`; the older top-level paths are absent.

Documentation updates cover `.env.example`, `docs/development/settings-and-environment.md`, `docs/gm/prompts.md`, and an explicit amendment to architecture design §9 allowing the model payload. BRIA's licence applies to the weight and its redistribution; image publishers and operators own licence compliance, including commercial use. The permissive ISNet model-selection escape hatch is removed.

This is one coupled, engineer-day change. It needs no dependency upgrade, database migration, compatibility alias, player command change, translation-model change, or new acquisition service. `docs/game/commands.md` and `docs/game/command-reference.md` stay unchanged because command behavior does not change. Implementation should extend existing test modules without moving them; shard ownership changes only if that assumption changes.

## Batch:

depends-on: none

code-conflicts: none within this batch (one change). Serialize with any future change editing the listed implementation surfaces or the three capability specifications. The currently active monster-AI and exploration changes are not dependencies; any shared-file edit encountered during apply requires integration review.
