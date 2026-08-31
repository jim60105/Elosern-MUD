# Proposal: art-output-format-pipeline

## Why

The reference plugin (`sd-webui-image-gen`) exposes in its settings UI three
output knobs we completely lack: `imageFormat` (the reference stores generated
images as AVIF/WebP/JPEG and only uses PNG as wire format), a JPEG/WebP
quality level (its converter runs at quality 80), and
`preserveGenerationMetadata` — an explicit switch that either keeps the
generation parameters readable inside the finished image or guarantees the
delivered image carries **no** metadata at all. Our worker is PNG-only end to
end (`expected_output_identity` hard-codes `.png`, `web/art_media.py` allowlists
only `.png`), so every stored artwork is a lossless PNG (typically 1–2 MB), the
webclient transfers them uncompressed at every panel render, and the
generation parameters (seed, sampler, sizes) silently depend on whatever
tEXt chunk sd-webui happened to embed.

The MUD needs the same degrees of freedom: an operator must be able to pick
the stored encoding and quality for their bandwidth/storage profile, and must
be able to guarantee privacy-preserving metadata removal on the art store
(this is an adult-content product; "ship images with zero generation metadata"
is a first-class deployment choice, exactly as the reference treats it).

PNG remains the wire format to/from sd-webui (the verified request pattern
forces `samples_format: "png"`; the conversion happens **locally**, as in the
reference — we never depend on the server's encoder). AVIF IS adopted:
Pillow ≥ 11.3.0 encodes AVIF natively (verified against Pillow 12.3.0
manylinux wheels — `features.check("avif")`, `exif=` round-trip, quality
option), so the format enum is the reference's full four: `png|webp|jpeg|avif`.

## What Changes

- Add **Pillow + piexif** as locked runtime dependencies (`uv add pillow
  piexif`): Pillow (≥ 11.3.0, native AVIF — verified against 12.3.0 wheels)
  is the decoder/encoder/validator, piexif writes the EXIF `UserComment`
  carrying generation parameters for JPEG/WebP/AVIF (the reference achieves
  the same by hand-rolling EXIF muxing in `exif-mux.ts`; a proven library
  beats a port).
- Add a format module `world/art/formats.py`: `encode(png_bytes) ->
  (bytes, ext)` converts the transport PNG to the configured output format at
  the configured quality, with generation-metadata policy applied
  (embed/keep vs guaranteed strip — D3).
- Add three env-overridable settings: `ART_SD_OUTPUT_FORMAT` (choice
  `png|webp|jpeg|avif`, default `png` = decoded-pixel-identical to today),
  `ART_SD_OUTPUT_QUALITY` (integer 1–100, default 80, matching the reference;
  meaningful for lossy formats), `ART_SD_PRESERVE_GENERATION_METADATA`
  (boolean word, default `True`). New typed helpers: a **choice** converter
  (case-insensitive membership, fail-closed) and a **maximum bound** on the
  integer helper (the reference bounds its knobs with min/max; today's helper
  is minimum-only).
- Format-aware output identities: `expected_output_identity` gains the
  configured extension; a successful regeneration under a **new extension**
  deletes exactly the record's prior identity file (under the store-root
  confinement check) after the atomic commit — no orphan pairs, no scan-based
  migration (unreleased project; the format switch takes effect on
  regenerated images, staff re-runs `@art requeue`/`retry` to convert the
  store, documented in the guide).
- Serve them: `web/art_media.py` allowlist accepts the four extensions with
  correct `Content-Type`s (`image/png|image/webp|image/jpeg|image/avif`).
- New bounded error code `sd_format_error` for encode/decode failures, settle
  path identical to every other named client error. `encode` rejects any
  input whose decoded format is not PNG (valid JPEG/WebP fail exactly like
  garbage), and every encode path works from a sanitized pixel copy so
  server-embedded text/EXIF/ICC can never pass through in either mode.
- `GeneratedImage` carries the exact provenance (prompt pair + generation
  parameters) of the request that produced it, so embedded metadata can never
  describe a later re-render of the mutable prompt library.
- The lease formula gains a bounded per-item local-conversion allowance
  (`N × (timeout + 60 s) + margin`) so a slow encode never gets reclaimed.
- The presenter validates a done record's STORED identity against the closed
  four-extension set (not equality with the configured format), so a format
  switch keeps every existing asset presenting until it is regenerated.

## Capabilities

### New Capabilities
- `art-output-format-pipeline`: local format conversion of generated art with
  quality control and explicit generation-metadata policy (embed or guarantee
  absence), format-consistent store identities and media serving.

### Modified Capabilities
- `art-queue-worker`: `expected_output_identity` carries the configured
  extension; settle deletes the prior identity only on an extension change;
  `sd_format_error` joins the named error set; the media-serving requirement's
  extension allowlist accepts png/webp/jpg/avif and maps each to its
  Content-Type.
- `settings-environment-overrides`: env-backed set grows from exactly 21 to
  exactly 24; typed-conversion section gains the choice family and the
  integer maximum bound.

(`webclient-art-panel` needs NO delta: its requirements already speak of
same-origin URLs derived from validated stored identities — format-agnostic.)

## Impact

- Dependencies: `pillow`, `piexif` via `uv add` (pyproject + uv.lock updated by
  the tool, never by hand).
- Code: new `world/art/formats.py`; `world/art/sd_worker.py` (`GeneratedImage`
  provenance fields, filled from the built request);
  `world/art/worker.py` (identity ext, encode step, provenance passthrough,
  prior-file deletion on ext change, `sd_format_error`, lease allowance);
  `world/art/queue.py` (`settle_generated` validates both identities and
  returns the committed prior as the post-commit cleanup candidate);
  `world/art/presenter.py` (closed-set stored-identity validation);
  `web/art_media.py` (extension allowlist + Content-Types);
  `server/conf/settings.py` (3 settings + `_env_choice` + maximum kwarg +
  derived extension); `server/conf/test_settings.py` pop list grows to 24.
- Docs: `.env.example` (3 entries), guide (24-row inventory + format-switch
  procedure), `docs/gm/prompts.md` table.
- Tests: new `world/art/tests/test_formats.py` (real Pillow encodes —
  deterministic, no network; assertions via decoded pixels + format-aware
  metadata inspection, not encoder byte stability; no shard-manifest change
  — the `world.art` label already covers the package), existing
  `web/webclient/tests/test_art_media.py` extended for webp/jpeg/avif
  serving, `test_worker.py` extension/migration cases, env-override table
  updates.
- No player command surface changes; `tests/test_command_docs.py` untouched.

## Dependency note

**Must land after `art-generation-config-parity`** (A). Both changes edit the
same env-inventory tables, `.env.example`, guide tables, and
`settings-environment-overrides` delta text; A also introduces the
`GeneratedImage` result this change encodes from. Apply strictly serially
A → B.
