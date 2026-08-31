# Tasks: art-output-format-pipeline

## 1. Dependencies + settings

- [ ] 1.1 `uv add pillow piexif` (never edit `uv.lock` by hand); confirm the
  Containerfile needs no changes (manylinux wheels).
- [ ] 1.2 Add `_env_choice(name, choices, default)` and an inclusive
  `maximum=` keyword to `_env_int` in `server/conf/settings.py`, same
  ImproperlyConfigured error shape and rule-phrasing convention.
- [ ] 1.3 Add `ART_SD_OUTPUT_FORMAT` (`_env_choice`,
  `("png","webp","jpeg","avif")`,
  default `"png"`), `ART_SD_OUTPUT_QUALITY` (`_env_int` positive, maximum 100,
  default 80), `ART_SD_PRESERVE_GENERATION_METADATA` (`_env_bool`, default
  True); derive `ART_SD_OUTPUT_EXTENSION` at the END of `settings.py`, AFTER
  the `secret_settings` import (mirroring the post-import
  `build_profiles` validation precedent), from the final effective format via
  the closed map — so a secret-overridden format flows into the extension and
  any direct extension assignment (env or secret) is unconditionally
  replaced. The extension appears in NO inventory table and no `.env.example`
  and performs no env read.
- [ ] 1.4 Grow `ENV_BACKED`/`DEFAULT_REPR`/`VALID_OVERRIDES` in
  `server/conf/tests/test_env_overrides.py` to exactly 24 entries (choice +
  inclusive-bound rows: quality 1/100 valid, 0/101 invalid; format case
  variants; `heic` invalid); update the AST inventory expectations and the
  `_test_settings_popped_names` pop list in `server/conf/test_settings.py`
  (→ 24, extension NOT included — it has no env read); add derivation tests:
  secret-file `ART_SD_OUTPUT_FORMAT` override ⇒ extension follows; direct
  `ART_SD_OUTPUT_EXTENSION` assignment via env or secret is discarded in
  favor of the derived value.

## 2. Format module

- [ ] 2.1 Create `world/art/formats.py`: `encode(png_bytes, *, prompt,
  negative_prompt, steps, cfg_scale, sampler, scheduler, width, height,
  seed, checkpoint, output_format, quality, preserve_metadata) -> tuple[bytes, str]`
  returning `(bytes, settings.ART_SD_OUTPUT_EXTENSION)`; PNG = Pillow
  lossless re-save, WebP/JPEG/AVIF = Pillow encode at quality (verified: the
  Pillow ≥ 11.3 AVIF encoder accepts `exif=`/`quality=`); JPEG encodes from
  `convert("RGB")` (Pillow raises `OSError` on RGBA); non-decodable input
  → `SDError("sd_format_error", ...)`.
- [ ] 2.2 Metadata ON: A1111-shaped parameters text built from the passed
  engine-known values — seed entry OMITTED entirely when `seed is None` (no
  `Seed:` line, no sentinel), checkpoint line when set; PNG via `PngInfo`
  tEXt `parameters`; JPEG, WebP, and AVIF via piexif EXIF `UserComment` with
  the pinned ASCII prefix (`"ASCII\x00\x00\x00"`), all three passing the
  same piexif bytes via `exif=`.
- [ ] 2.3 Metadata OFF: strip by construction (empty `PngInfo` on re-save —
  zero text chunks; no `exif=`/`icc_profile=` on encode); never pass server
  chunks through in either mode.
- [ ] 2.4 `world/art/tests/test_formats.py` with FORMAT-AWARE metadata
  inspection (no byte-marker scanning): parse every PNG ancillary chunk type
  (assert no `tEXt`/`zTXt`/`iTXt`/`eXIf`/`iCCP` when OFF), parse JPEG
  APP-segments and WebP RIFF chunks (assert no EXIF/XMP/ICC when OFF),
  assert AVIF output's `Image.info` is free of exif/xmp/icc when OFF; ON
  round-trip per format — PNG via `Image.info["parameters"]`, JPEG/WebP/AVIF
  via `piexif.load(image.info["exif"])` byte-comparing `UserComment`
  (decoded past the ASCII prefix) against the generated text; OFF fixtures
  deliberately carry `tEXt`, `iTXt`, EXIF, and ICC inputs and assert the
  original parameter text is absent from every output; decoded-pixel
  equality for the default png path (NOT byte equality); dimension
  preservation; magic bytes per format (incl. the AVIF `ftyp`/`avif` brand);
  quality monotonicity on noise; RGBA-source jpeg normalization succeeds;
  non-PNG → `sd_format_error`; seedless output contains no seed token. No
  shard-manifest change (label `world.art` covers the package; verify with
  the ownership-contract test).

## 3. Worker wiring

- [ ] 3.1 `expected_output_identity` uses `settings.ART_SD_OUTPUT_EXTENSION`;
  `_settle_one` calls `formats.encode` between `client.generate` and
  `_write_temp`, mapping its failure to `sd_format_error` (prior output
  retained).
- [ ] 3.2 Extension-change settle in STRICT order (design D5): validate both
  identities under root → install new file → transition the record under the
  queue lock → delete the prior identity ONLY after the transition succeeds;
  a deletion error never reverts the transition (bounded `cleanup_failed`
  log, unreferenced orphan, next regen cleans); same-extension settles delete
  nothing.
- [ ] 3.3 Assemble `encode` kwargs from record + settings; persist seed as in
  change A; `tests/test_worker.py`: extension-aware identity, format-change
  replaces+deletes prior, same-extension deletes nothing, encode failure
  retains prior + settles `sd_format_error`, settle failure BEFORE deletion
  leaves the prior file on disk AND referenced, forced deletion error leaves
  the committed transition intact with an orphan.

## 4. Media serving

- [ ] 4.1 `web/art_media.py`: allowlist
  `^(scene|portrait/monster|portrait/character)/[^/]+\.(png|webp|jpg|avif)$`;
  closed extension→mime map (`image/png|webp|jpeg|avif`); confinement,
  done-record requirement, and 404 behavior unchanged.
- [ ] 4.2 Extend `web/webclient/tests/test_art_media.py`: webp + jpg + avif
  served with correct Content-Type, `.jxl`/no-ext 404, mixed-store serving
  (png file under avif config), all existing rejections unchanged.

## 5. Docs + inventory

- [ ] 5.1 `.env.example`: `#ART_SD_OUTPUT_FORMAT=png`,
  `#ART_SD_OUTPUT_QUALITY=80`, `#ART_SD_PRESERVE_GENERATION_METADATA=true`
  with type/range/semantics comments (quality = lossy only; OFF ⇒ provably
  metadata-free; default png is pixel-identical, container bytes may differ).
- [ ] 5.2 `docs/development/settings-and-environment.md`: 24-row inventory +
  derived-setting note + format-switch procedure (switch → `@art retry`/
  `@art requeue` regenerates; mixed store serves correctly until then).
- [ ] 5.3 `docs/gm/prompts.md`: rows for the three knobs (environment
  variables column).

## 6. Verification

- [ ] 6.1 Focused: `MUD_TEST_SETTINGS=1 uv run --locked evennia test
  --settings test_settings.py --keepdb world.art server.conf web.webclient`
  green; `compileall -q world server web`; `git diff --check`.
- [ ] 6.2 `openspec validate art-output-format-pipeline --strict`.

## 7. Archive-time traceability sync (after implementation is verified)

- [ ] 7.1 Annotate tests with `@covers_requirement` literal IDs (two
  new-capability requirements, two MODIFIED worker requirements, MODIFIED
  settings requirements, ADDED derived-extension requirement), then sync this
  change's deltas into `openspec/specs/` and land code + tests + spec sync +
  archive as one commit chain (the `env-overridable-settings` archive
  precedent); confirm IDs against `uv run --locked python -m
  tools.spec_traceability list` — the check gate only accepts them once the
  specs are synced. C's implementation may not start before this archive
  completes (C's MODIFIED settings requirement restates the synced post-B
  text).
