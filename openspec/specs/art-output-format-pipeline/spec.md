# art-output-format-pipeline Specification

## Purpose
Convert generated art locally from the sd-webui PNG transport into the
operator-configured output format (`png`, `webp`, `jpeg`, or `avif`) at the
configured quality, with an A1111-compatible generation-metadata policy that
embeds the engine-known provenance when preserved and is provably absent when
not — keeping the wire protocol PNG-only and the failure taxonomy bounded to
the existing named error codes.

## Requirements

### Requirement: Generated art is converted locally to the configured output format at the configured quality
`world/art/formats.py::encode(...)` SHALL convert the transport PNG bytes of a
`GeneratedImage` into the format named by `ART_SD_OUTPUT_FORMAT` (`png`,
`webp`, `jpeg`, or `avif`) at `ART_SD_OUTPUT_QUALITY` (1–100), returning the
encoded bytes together with the store extension for that format. Encoding a non-PNG
or corrupted input SHALL raise the named `SDError` code `sd_format_error` before any
output is produced.

#### Scenario: WebP output is produced at the configured quality
- **WHEN** `ART_SD_OUTPUT_FORMAT=webp` and `ART_SD_OUTPUT_QUALITY=60` and a valid PNG is encoded
- **THEN** the returned bytes start with the WebP RIFF/WEBP magic, decode to the same dimensions,
  carry extension `.webp`, and the same conversion at quality 100 on noisy content yields a
  larger encoding than at 60 (the size-ordering assertion is required for WebP only; JPEG/AVIF
  tests assert decode, container, dimensions, and extension without a byte-size ordering)

#### Scenario: JPEG output carries the .jpg extension
- **WHEN** `ART_SD_OUTPUT_FORMAT=jpeg` and a valid opaque PNG is encoded
- **THEN** the returned bytes start with the JPEG SOI magic and the extension
  is `.jpg`

#### Scenario: AVIF output is produced with the avif brand
- **WHEN** `ART_SD_OUTPUT_FORMAT=avif` and a valid PNG is encoded
- **THEN** the returned bytes parse as an ISOBMFF container with the `avif`
  major brand, decode to the same dimensions, and carry extension `.avif`

#### Scenario: An RGBA source normalizes for JPEG instead of failing
- **WHEN** `ART_SD_OUTPUT_FORMAT=jpeg` and the decoded PNG carries an alpha
  channel
- **THEN** encoding succeeds via the RGB normalization and no
  `sd_format_error` is raised

#### Scenario: The default png format never changes pixels
- **WHEN** `ART_SD_OUTPUT_FORMAT` is unset and a valid PNG is encoded with
  metadata preservation on
- **THEN** the decoded pixels equal the input's decoded pixels and the output
  remains a valid PNG

#### Scenario: Corrupted or non-PNG transport bytes fail with the named code
- **WHEN** `encode` receives bytes that are not a decodable PNG, a truncated PNG whose header is
  valid, or a decodable valid JPEG or WebP
- **THEN** it raises `SDError` with code `sd_format_error` and nothing is written to the store

#### Scenario: The png conversion is a lossless re-save with the D3 policy
- **WHEN** `ART_SD_OUTPUT_FORMAT=png`
- **THEN** the conversion is a lossless Pillow re-save with the metadata policy of D3 applied, so the
  policy can never be bypassed by the format choice

#### Scenario: The encoder normalizes the decoded image to each format's accepted mode
- **WHEN** an image is encoded for any format
- **THEN** the encoder normalizes the decoded image to the mode each format accepts — JPEG is encoded
  from an RGB view, and Pillow's `convert("RGB")` drops any alpha channel

#### Scenario: The format check demands a decoded format of PNG
- **WHEN** the input decodes as a *valid* JPEG or WebP
- **THEN** it is rejected exactly like garbage — the decoded image's format must be PNG

#### Scenario: Quality affects lossy formats only
- **WHEN** `ART_SD_OUTPUT_QUALITY` is varied
- **THEN** it affects lossy formats only

#### Scenario: The default png pipeline matches the verbatim-PNG path byte-for-byte in pixels
- **WHEN** the default `png` pipeline runs
- **THEN** it keeps pixel-identical output to today's verbatim-PNG path

#### Scenario: The returned store extension per format
- **WHEN** `encode` returns
- **THEN** the extension is `.png`, `.webp`, `.jpg`, or `.avif` for the respective format

#### Scenario: The wire protocol stays PNG-only
- **WHEN** the output format is configured away from `png`
- **THEN** the sd-webui wire format remains PNG — no request behavior changes

#### Scenario: No other error taxonomy is introduced
- **WHEN** the encoder's failure modes are enumerated
- **THEN** `sd_format_error` is the only named code this pipeline adds; no other error taxonomy is
  introduced

### Requirement: Generation metadata is embedded when preserved and provably absent when not
When `ART_SD_PRESERVE_GENERATION_METADATA` is true, the encoded output SHALL
carry the A1111-shaped generation-parameters text in the format-native location:
PNG a text chunk with key `parameters`; JPEG, WebP, and AVIF EXIF `UserComment`.
When the setting is false, the delivered artifact SHALL carry no generation metadata at all.

#### Scenario: Preserved metadata round-trips from the encoded artifact
- **WHEN** metadata preservation is on and a png, webp, jpeg, or avif image
  is encoded and written
- **THEN** reading the stored file back yields the generation-parameters text
  containing the prompt and the recorded seed (PNG via the `parameters` text
  chunk; JPEG, WebP, and AVIF via the EXIF `UserComment` parsed with piexif)

#### Scenario: Stripping guarantees absence
- **WHEN** `ART_SD_PRESERVE_GENERATION_METADATA=false` and each of png, webp, jpeg, avif is
  encoded from an input PNG carrying `tEXt`, `iTXt`, EXIF, and ICC fixtures
- **THEN** none of the four outputs carries any metadata chunk, EXIF/XMP/ICC payload, or the
  original parameter text

#### Scenario: Preservation adds its own block without inheriting the source's
- **WHEN** `ART_SD_PRESERVE_GENERATION_METADATA=true` and each format is encoded from the same
  metadata-laden input fixture
- **THEN** the output's metadata is exactly the regenerated parameters text — no source ICC
  profile, no source EXIF, and no source text chunk other than the regenerated `parameters`

#### Scenario: A seedless record fabricates no seed
- **WHEN** metadata preservation is on and the generated image's seed is
  `None`
- **THEN** the parameters text omits the seed entry entirely

#### Scenario: The parameters text's fields
- **WHEN** metadata preservation is on
- **THEN** the text carries prompt, negative prompt, steps, CFG scale, sampler, scheduler, width,
  height, and — when the record carries one — the seed, plus the configured checkpoint when set

#### Scenario: The PNG text chunk flavor follows the text's encoding
- **WHEN** the parameters text is written into a PNG
- **THEN** it uses `tEXt` for Latin-1-safe text and `iTXt` otherwise

#### Scenario: Every encode works from a sanitized pixel copy
- **WHEN** any encode runs — metadata preservation ON or OFF alike
- **THEN** it works from a sanitized pixel copy of the decoded source carrying no source metadata (an
  empty `.info`), so server-embedded text, EXIF, or ICC can never survive by encoder pass-through in
  either mode: the parameters block is regenerated from engine-known values, never copied wholesale
  from server-supplied chunks

#### Scenario: The stripped form per format
- **WHEN** `ART_SD_PRESERVE_GENERATION_METADATA=false`
- **THEN** PNG output is re-saved with zero text chunks, and JPEG/WebP/AVIF output is encoded without
  EXIF or ICC

#### Scenario: Verification is format-aware inspection, never byte-marker scanning alone
- **WHEN** absence of metadata is verified
- **THEN** every PNG ancillary chunk type is parsed (no `tEXt`, `zTXt`, `iTXt`, `eXIf`, or `iCCP`),
  JPEG APP-segments and WebP RIFF chunks are parsed (no EXIF, XMP, or ICC payload), AVIF `Image.info`
  is checked free of `exif`/`xmp`/ICC, and the original server parameter text is asserted absent

### Requirement: An alpha channel survives every alpha-capable output format

`world/art/formats.py::encode(...)` SHALL preserve the alpha channel of an RGBA transport
PNG end to end for each of the three alpha-capable output formats — `png`, `webp`, and
`avif` — so a transparent-background artifact produced upstream is still transparent after
it is stored.

#### Scenario: Alpha round-trips through each alpha-capable format
- **WHEN** an RGBA PNG with a fully transparent region is encoded with
  `ART_SD_OUTPUT_FORMAT` set to `png`, then `webp`, then `avif`
- **THEN** each encoded artifact decodes to an alpha-carrying mode whose pixels in that
  region are fully transparent, and the opaque region stays opaque

#### Scenario: Alpha survives with metadata stripping on
- **WHEN** the same RGBA PNG is encoded for each alpha-capable format with
  `ART_SD_PRESERVE_GENERATION_METADATA=false`
- **THEN** the transparency is preserved identically and the artifact still carries no
  metadata chunk, EXIF/XMP/ICC payload, or source parameter text

#### Scenario: An opaque source is unaffected
- **WHEN** an opaque RGB PNG is encoded for each of the four supported formats
- **THEN** the stored output is unchanged from the pre-change pipeline's output for that
  format

#### Scenario: The decoded alpha check in both metadata modes
- **WHEN** the encoded bytes are decoded
- **THEN** the image's mode carries alpha and its fully transparent source pixels are still fully
  transparent, in both metadata modes (`ART_SD_PRESERVE_GENERATION_METADATA` true and false)

#### Scenario: The sanitizing pixel copy preserves the source mode
- **WHEN** the encoder builds its sanitized working copy
- **THEN** it copies the source mode rather than flattening it

#### Scenario: JPEG alpha behavior is unchanged
- **WHEN** `ART_SD_OUTPUT_FORMAT=jpeg`
- **THEN** the existing behavior stands: JPEG accepts no alpha and continues to be encoded from an
  RGB view, which is why the `art-portrait-cutout` capability refuses the `jpeg` + background-removal
  combination at settings import rather than allowing a silent flatten
