---
name: art-default-portraits-transparent
description: Regenerate the six committed default portraits through the existing generate → cutout → encode pipeline
additional_files:
  - design.md
  - tasks.md
  - specs/art-gallery-fallback/spec.md
---

## Why

The six built-in fallback portraits (`web/static/art/defaults/{man,woman,boy,girl,elder,monster_anon}.webp`) are opaque RGB images painted on a light, flat backdrop. They are what a fresh database, every Storybook story, and every subject without generated art shows on the AVG stage, and on the dark stage their backdrop survives the stage actor's mask as a pale halo (the "sticker" look in the UI/UX review, `sb1080/core-appshell--combat-hud.png`, `live/13-skills.png`). Generated portraits already avoid this: the worker's cutout stage (`world/art/cutout.py`, applied in `world/art/worker.py::_settle_one` between `generate` and `encode`) stores every character and monster portrait with its background removed. Only the committed defaults were never run through that pipeline.

The fix is to do for the six static defaults what the runtime does for every generated portrait: render each one from the project prompt library (`art.portrait_prompt` / `art.negative_prompt` in `prompts/art.yaml`) through `SDWebUIClient.generate`, remove its background with `world.art.cutout.remove_background`, and encode it with `world.art.formats.encode` into the committed `.webp`. No new pipeline, model choice, or runtime stage is involved; a one-shot operator tool calls the existing seams and its output is committed.

**Implementation profile:** logic plus asset generation. The deliverable is one maintenance tool, six regenerated image files, re-authored face rectangles, and a contract test that decodes each committed default for an alpha channel with transparent corners and an opaque figure. A person still has to look at each cut edge and re-author each face rectangle (tasks 2.2 and 2.3).

## What Changes

- New one-shot maintenance tool `tools/regenerate_default_art.py`:
  - bootstraps Django settings (the same `DJANGO_SETTINGS_MODULE=server.conf.settings` + `django.setup()` pattern `tools/test_data_lint.py` uses), because `world.art.cutout` and `world.art.sd_worker` read Evennia settings;
  - for each of the six `FALLBACK_KEYS`, builds the subject (`ArtSubject` character kind for the five figure keys, monster kind for `monster_anon`) and an authored, deterministic description sentence, then calls the resolved SD client's `generate()` — the existing seam that renders `art.portrait_prompt`/`art.negative_prompt` and honors the `ART_SD_*` knobs — followed by `cutout.remove_background()` and `formats.encode()` into WebP;
  - refuses to write a file without alpha or at/over `FALLBACK_MAX_FILE_BYTES`; supports `--key` to re-run one key.
  It is not imported by the game, the worker, or any test. It is run by hand with sd-webui reachable, and its output is committed.
- `web/static/art/defaults/*.webp`: the six files are replaced by transparent RGBA WebP rendered on the configured portrait canvas (`ART_SD_PORTRAIT_WIDTH`/`HEIGHT`, 768×1024 by default). Keys, file names, and extension are unchanged.
- `world/art/gallery_fallback.py`: `FALLBACK_FACE_RECTS` is re-authored against the regenerated pixels (the figures are re-rendered, so the old rectangles are not assumed to survive).
- `world/art/tests/test_gallery_fallback.py`: a new contract test decodes each committed default and checks it for an alpha channel, fully transparent corner regions, and an opaque centre band where the figure stands.
- No change to `world/art/cutout.py`, `world/art/sd_worker.py`, `world/art/formats.py`, the worker, the OOB protocol, or the webclient.

Out of scope:
- The stage's own treatment of transparent art (drop shadow, ground shadow, and the mask only for images without alpha): `webclient-stage-actor-grounding`.
- Generated portraits: they already go through the cutout stage.
- Scene backdrops: scenes are never cut out.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `art-gallery-fallback`: ADDED "The built-in fallback images carry a transparent background".

## Impact

- Assets: `web/static/art/defaults/*.webp` (six binary files replaced).
- New: `tools/regenerate_default_art.py`.
- Modified: `world/art/gallery_fallback.py` (`FALLBACK_FACE_RECTS` values only).
- Tests: `world/art/tests/test_gallery_fallback.py` (already registered in `.github/evennia-shards.json`; no new module).
- Spec traceability: one new ID, `art-gallery-fallback::the-built-in-fallback-images-carry-a-transparent-background`.
- Runtime prerequisites for the regeneration run (operator-side, documented in the tasks): a reachable sd-webui endpoint, and the permissive `isnet-anime` cutout model artifact present locally (`ART_REMBG_MODEL=isnet-anime`, artifact pre-placed or `ART_REMBG_DOWNLOAD_ENABLED` set for the run) — the committed images must not depend on the BRIA-licensed default `bria-rmbg` weights.
- Dependencies: none in code. `webclient-stage-actor-grounding` is easier to judge after it lands (its stories use these images), but does not depend on it in code.
