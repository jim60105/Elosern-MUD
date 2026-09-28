## 1. Tool

- [ ] 1.1 Create `tools/regenerate_default_art.py` per design D1–D3:
  - a module docstring stating that it is a one-shot maintenance script, that its output is committed, and why the run pins the permissive `isnet-anime` cutout model
  - bootstrap Django the way `tools/test_data_lint.py` does (`DJANGO_SETTINGS_MODULE=server.conf.settings` default + `django.setup()`) before importing `world.art.*`
  - module-level mapping from each `FALLBACK_KEYS` key to `(ArtSubject kind, authored English description sentence)` per design D2 (character kind for `man`/`woman`/`boy`/`girl`/`elder`, monster kind for `monster_anon`)
  - per key: `resolve_sd_client().generate(subject, description)` → `cutout.remove_background(image.data)` → `formats.encode(...)` with the same WebP quality/metadata arguments the worker passes in `world/art/worker.py::_settle_one`; write `web/static/art/defaults/<key>.webp` only when the decoded image carries alpha and is below `FALLBACK_MAX_FILE_BYTES`, otherwise refuse and name the key
  - `--key <key>` regenerates one file; the tool overrides the cutout model at the call site (`override_settings(ART_REMBG_MODEL="isnet-anime")`, not an ambient env assumption); only explicit `--allow-bria` selects the ambient configured model instead (never used for committed defaults)
  - refuses to start generation when the resolved cutout model is unavailable offline unless `--allow-download` is passed and `ART_REMBG_DOWNLOAD_ENABLED` is honored (operator pre-places the artifact otherwise)

  Verify: `DJANGO_SETTINGS_MODULE=server.conf.settings uv run --locked python tools/regenerate_default_art.py --help` prints usage without contacting sd-webui or loading a model.

## 2. Assets

- [ ] 2.1 Operator prerequisite: sd-webui reachable at `ART_SD_BASE_URL`; place the `isnet-anime` model artifact in `server/.rembg` (or export `ART_REMBG_MODEL=isnet-anime` plus the download switch for the session). Run `ART_REMBG_MODEL=isnet-anime uv run --locked python tools/regenerate_default_art.py`. Verify for each file: `uv run --locked python -c "from PIL import Image; im=Image.open('web/static/art/defaults/<key>.webp'); print(im.mode, im.size)"` prints `RGBA` at the configured `ART_SD_PORTRAIT_*` canvas, and `stat -c %s` for each file is below `FALLBACK_MAX_FILE_BYTES` (409,600 bytes) — a lossy-alpha WebP over the bound must be re-encoded at lower quality before commit.
- [ ] 2.2 Check each of the six outputs by eye, composited on `#0b0d10` and on `#e7e0d1` (for example with a throwaway Pillow composite in the scratchpad, never committed). No backdrop fragments may remain, and no hair, hand, or cloak edge may be eaten. Re-run any failing key with `--key <key>` (new seed). Record in the commit message which keys needed re-runs.
- [ ] 2.3 Re-author `FALLBACK_FACE_RECTS` in `world/art/gallery_fallback.py` against the new pixels (normalized unit-square rects, measured on each committed file; design D5). Verify the existing face-rect shape tests in `test_gallery_fallback.py` still pass with the new values.

## 3. Contract test

- [ ] 3.1 In `world/art/tests/test_gallery_fallback.py`, add `test_every_default_has_a_transparent_background` to `ClosedVocabularyContractTests`, per design D4 (RGBA mode, 24×24 corner squares with alpha 0, mean alpha ≥ 250 in the centre band). Assert the geometry against `FALLBACK_MAX_FILE_BYTES` and the decode itself, not a hardcoded pixel size (the canvas is settings-driven). Annotate with `@covers_requirement("art-gallery-fallback::the-built-in-fallback-images-carry-a-transparent-background")` (confirm the ID with `uv run --locked python -m tools.spec_traceability list`).
- [ ] 3.2 Prove that the new test fails on an opaque image: point it at the pre-change file (`git show HEAD:web/static/art/defaults/man.webp > <scratchpad>/man.webp`) via a temporary directory override. Observe the failure, then revert.
- [ ] 3.3 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.art.tests.test_gallery_fallback world.art.tests.test_presenter` (with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input). All green.

## 4. Specs and validation

- [ ] 4.1 Sync the delta into `openspec/specs/art-gallery-fallback/spec.md`. `uv run --locked python -m tools.spec_traceability check` is green.
- [ ] 4.2 `openspec validate art-default-portraits-transparent --strict` passes.
