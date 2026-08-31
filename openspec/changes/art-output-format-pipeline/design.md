# Design: art-output-format-pipeline

## Context

After change A, the client returns `GeneratedImage(data: bytes, seed: int |
None)` with validated PNG transport bytes; the worker writes those bytes
verbatim to `scene/<key>.png` (etc.) and `web/art_media.py` serves only
`.png`. The reference plugin converts PNG **locally** to
avif/webp/jpeg/png via sharp at quality 80 and carries A1111-style generation
parameters through its own EXIF muxer, with a `preserveGenerationMetadata`
switch whose OFF state guarantees the delivered image carries no metadata at
all. Its A1111 parameter block it embeds is the canonical
`prompt\nNegative prompt: x\nSteps: n, Sampler name: s, ...` text (the same
shape sd-webui itself writes into PNG `parameters` tEXt chunks, which is what
tooling like image-info readers parse back).

Constraints: the deterministic core owns all state writes (conversion is pure
bytes→bytes in the client boundary's aftermath; only the worker/service
touch the store); the art store lives on the persistent volume and the media
route confinement rules are non-negotiable; no released users means format
switches may require requeues instead of migrations.

## Goals / Non-Goals

**Goals:**

- Operator-selected stored encoding + quality with fail-closed typing, over
  the reference's full four-format set (`png|webp|jpeg|avif`).
- Explicit, tested metadata policy: ON = generation parameters embedded and
  readable; OFF = provably zero metadata in the delivered artifact.
- One file per subject at all times (extension change replaces, never
  orphans).
- Default `png` keeps decoded pixels and the `.png` identity identical to
  today (it intentionally re-encodes through Pillow to enforce the metadata
  policy; container bytes may differ from the transport PNG).

**Non-Goals:**

- Server-side format negotiation (`samples_format` stays `png`; sd-webui's
  WebP/JPEG paths vary by fork — local conversion is the verified reference
  behavior).
- Rescaling/downscale pipelines, background removal, upscalers — not in the
  reference's settings surface either.
- Rewriting existing store files at boot/migration (unreleased; staff
  requeue converts on demand).

## Decisions

### D1 — Pillow (≥ 11.3.0, native AVIF) + piexif, both pure-`uv add` locked deps

Pillow decodes the transport PNG, re-encodes WebP/JPEG/AVIF, writes PNG
`tEXt`, and is already the de-facto stdlib-adjacent choice for this role.
AVIF is NOT a reason to add another plugin: native AVIF encode/decode landed
in Pillow 11.3.0, and adoption was empirically verified against the
12.3.0 manylinux wheel (`features.check("avif")` true; `save(fmt="AVIF",
exif=piexif_bytes, quality=N)` succeeds; `Image.info["exif"]` round-trips
the UserComment byte-for-byte). The lock pins whatever `uv add pillow`
resolves (≥ 11.3.0 by construction). piexif writes EXIF `UserComment`
(JPEG/WebP/AVIF all take `exif=` bytes) without hand-rolling EXIF binaries
(the reference hand-rolls `exif-mux.ts`, ~800 lines with its own test suite —
not worth porting). Verified encoder fact baked into `encode`: JPEG cannot
take RGBA (raises `OSError`); `encode` normalizes the decoded image with
`convert("RGB")` for jpeg and `convert("RGBA")` only where alpha is legal.
Alternative: keep PNG-only + strip tooling — rejected: loses the bandwidth
knob that motivates the change (webclient art panels ship 1 MB+ PNGs).

### D2 — Conversion lives in `world/art/formats.py`, called by the worker, not the client

`encode(png_bytes, *, prompt, negative_prompt, steps, cfg_scale, sampler,
scheduler, width, height, seed, checkpoint, output_format, quality,
preserve_metadata) -> tuple[bytes, str]` returns `(bytes, extension)`. The
**worker** calls it between `client.generate` and `_write_temp`, because the
sd-worker client is the *transport* boundary (its tests use a fake transport
with fixed bytes and must stay socket-free and Pillow-free), while the worker
already owns store-layout policy (identity, temp file, atomic replace).
Failure of decode/encode raises `SDError("sd_format_error", ...)` — settle
path identical to all named errors (prior output retained). `encode` assembles
the A1111-shaped parameters text itself from the passed fields (single
source of truth for the shape; prompt digest is NOT included; the text
carries prompt, negative prompt, steps, cfg, sampler, scheduler, sizes, seed
entry omitted when `None`, checkpoint line when configured) — the worker
supplies data, never pre-formats it.

### D3 — Metadata policy semantics (mirrors the reference exactly)

- **ON (`ART_SD_PRESERVE_GENERATION_METADATA=True`, default):** output carries
  the A1111-shaped `parameters` text — PNG `tEXt` key `parameters` (via
  `PngInfo`); JPEG/WebP/AVIF EXIF `UserComment` written with piexif —
  verified that all three of Pillow's WebP, JPEG, and AVIF encoders accept
  the same piexif-produced `exif=` bytes and expose them back on
  `Image.info["exif"]`. sd-webui's own tEXt chunks from the transport PNG are
  NOT copied wholesale; the block is regenerated from known values so OFF⇒ON
  never leaks unknown server-embedded fields. Read-back for tests AND for any
  future ingest is defined concretely per container: PNG via
  `Image.info["parameters"]`; JPEG/WebP/AVIF via
  `piexif.load(image.info["exif"])` comparing `Exif.Image.UserComment`
  (decoded per the piexif charset prefix) byte-for-byte against the generated
  text, plus a container-level EXIF presence assertion. `UserComment`
  encoding is pinned: piexif `USER_COMMENT` with a fixed ASCII prefix
  (`"ASCII\x00\x00\x00"`), so the write and read sides are byte-stable.
- **OFF:** strip is guaranteed by construction — PNG re-saved with an empty
  `PngInfo` (no text chunks at all), JPEG/WebP/AVIF encoded from raw pixel
  data with no `exif=`/`icc_profile=` arguments. The test obligation is
  **format-aware metadata inspection, not marker scanning**: parse every PNG
  ancillary chunk type and assert none of `tEXt`/`zTXt`/`iTXt`/`eXIf`/`iCCP`
  is present; parse JPEG APP-segments and WebP RIFF chunks and assert no
  EXIF/XMP/ICC payload; for AVIF (ISOBMFF) assert `Image.open(...).info`
  exposes no `exif`/`xmp` and no ICC profile and the parameter text is
  absent. ON-input fixtures deliberately carry `tEXt`, `iTXt`, EXIF, and ICC
  so a silent encoder pass-through cannot pass the OFF suite, matching the
  reference's promise "關閉後輸出的圖片不會夾帶任何描述資訊".
- Seed availability: seed comes from change A's `GeneratedImage.seed`; when
  `None` the seed entry is **omitted from the parameters text entirely**
  (never a `None`/sentinel token).

### D4 — Settings: `_env_choice` + integer `maximum`, inventory 21 → 24

Extend the existing helper family (same module, same error shape `setting
<NAME>: invalid environment value '<raw>' (<rule>)`):
`_env_choice(name, choices, default)` case-insensitive membership, rule text
`expected one of png/webp/jpeg/avif (case-insensitive)`; `_env_int` gains keyword
`maximum` (INCLUSIVE — quality 100 must be legal), rule
`expected an integer between <min+1> and <max>` phrased per family. Three new
knobs: `ART_SD_OUTPUT_FORMAT` (choice, default `"png"`),
`ART_SD_OUTPUT_QUALITY` (int, minimum=0 exclusive ⇒ positive, maximum=100,
default 80), `ART_SD_PRESERVE_GENERATION_METADATA` (bool word, default True).
`ENV_BACKED`/pop-list/inventory tables grow to exactly 24; `.env.example` and
guide rows follow the established row contract (type, default, bounds).

### D5 — Extension-aware identities + delete-on-change extension migration

`expected_output_identity(subject)` uses `ART_SD_OUTPUT_EXTENSION`, derived
**at the very end of `settings.py`, after the `secret_settings` import**
(line ~315), from the final effective `ART_SD_OUTPUT_FORMAT` via the closed
map `{"png": ".png", "webp": ".webp", "jpeg": ".jpg", "avif": ".avif"}`
defined at the point of derivation. Deriving after the import makes the
extension immune to every
override path: a secret override of the FORMAT is honored (extension follows
the overridden format), and any direct `ART_SD_OUTPUT_EXTENSION` assignment —
env, `settings`, or `secret_settings` — is unconditionally replaced, so a
PNG can never be named `.webp` or served under the wrong MIME type. The
setting is derived-only: it appears in NO inventory table, no `.env.example`,
and is asserted in the never-env inventory. `formats.py` and consumers read
`settings.ART_SD_OUTPUT_EXTENSION`, never re-deriving it (settings modules
must not import `world.art.*`). On successful settle, strict order: (1)
validate BOTH new and prior identity under the store root; (2) write temp +
atomic replace to the NEW identity (prior output still intact + still
referenced at this point); (3) under the queue lock, transition the record's
status/identity to the new file — this is the authoritative commit; (4) only
after the transition succeeds, if the prior identity has a different
extension, `os.unlink` it. A deletion error NEVER reverts the committed
transition: log a bounded `cleanup_failed` note, leave the orphan
unreferenced (never served; next regeneration cleans it). A same-extension
regeneration is the unchanged replace-only path (no delete). A settle that
fails at or before step (3) leaves the prior file on disk AND referenced —
prior-output retention unchanged. The media route allowlist becomes
`^(scene|portrait/monster|portrait/character)/[^/]+\.(png|webp|jpg|avif)$`
(the closed set of all four store extensions, so a mixed store during a
format switch stays servable) with `FileResponse(content_type=...)` chosen
from a fixed extension→mime map (`.jpg`→`image/jpeg`,
`.avif`→`image/avif`).

Risk accepted: two `done` identities for one subject can never coexist in a
record (single `output_identity` field), so an orphan is at worst a stale
unreferenced file — never served (route requires a `done`-record reference).

### D6 — Deterministic tests without byte-stability dependence

Pillow encoders are stable per version but not cross-version byte-identical,
so `test_formats.py` asserts per format (png/webp/jpeg/avif): decoded-pixel
equality for the default png path (never container byte equality);
decode(output).size == source size; format magic bytes match extension
(including the AVIF `ftypavif` brand); quality ON/OFF produce different sizes
for a noise PNG (quality knob is live); metadata ON round-trips the
parameters text via the D3 read-backs (PNG `Image.info["parameters"]`;
JPEG/WebP/AVIF via `piexif.load(image.info["exif"])` on `UserComment`); OFF
output passes format-aware metadata inspection (every PNG ancillary chunk
type parsed — no `tEXt`/`zTXt`/`iTXt`/`eXIf`/`iCCP`; JPEG APP-segments and
WebP RIFF chunks parsed — no EXIF/XMP/ICC; AVIF `info` free of
exif/xmp/icc), never byte-marker scanning; `sd_format_error` on non-PNG
input; RGBA input under `jpeg` succeeds via the D1 `convert("RGB")`
normalization. Worker tests inject `formats.encode` monkeypatch + one real
Pillow round-trip case; media tests extend the existing module for webp/jpeg/
avif serve + disallowed extension 404 unchanged.

## Risks / Trade-offs

- [New runtime deps enlarge the container image] → Pillow (~4 MB wheel) +
  piexif (~100 KB) accepted against a 1 MB+/image bandwidth win; both are
  manylinux wheels, no build-time toolchain; Containerfile unchanged.
- [AVIF encode is slower than WebP (AV1 codec) and the browser surface must
  support it] → encoding runs on the background worker thread under the
  existing bounded generation timeout, never the reactor; the webclient shows
  the image via the same same-origin `<img>` URL, and every browser that can
  render this SPA (Chromium/Firefox/Safari ≥ 16) decodes AVIF natively.
- [Metadata OFF then PNG passthrough temptation] → even at format=png, OFF
  re-encodes losslessly *through Pillow* with no tEXt (re-save, pixel
  identical, guaranteed clean) — never skip the policy.
- [Quality applied to PNG confuses operators] → documented: quality affects
  lossy formats only; PNG path ignores it (no quantization surprises).
- [Format switch mid-store] → old files persist until each subject is
  regenerated (`@art retry`/`requeue`); guide documents the switch procedure
  end to end; no automated bulk migration by design.
