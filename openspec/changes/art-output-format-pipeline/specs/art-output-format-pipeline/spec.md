# art-output-format-pipeline delta specification

## ADDED Requirements

### Requirement: Generated art is converted locally to the configured output format at the configured quality
`world/art/formats.py::encode(...)` SHALL convert the transport PNG bytes of a
`GeneratedImage` into the format named by `ART_SD_OUTPUT_FORMAT` (`png`,
`webp`, `jpeg`, or `avif`) at `ART_SD_OUTPUT_QUALITY` (1–100), returning the
encoded bytes together with the store extension for that format (`.png`,
`.webp`, `.jpg`, `.avif`). The sd-webui wire format SHALL remain PNG — no
request behavior changes. For `png` the conversion SHALL be a lossless Pillow
re-save with the metadata policy of D3 applied, so the policy can never be
bypassed by the format choice. The encoder SHALL normalize the decoded image
to the mode each format accepts (JPEG is encoded from an RGB view; Pillow's
`convert("RGB")` drops any alpha channel). Encoding a non-PNG or corrupted
input SHALL raise the named `SDError` code `sd_format_error`; no other error
taxonomy is introduced. Quality SHALL affect lossy formats only. The default
`png` pipeline SHALL keep pixel-identical output to today's verbatim-PNG path.

#### Scenario: WebP output is produced at the configured quality
- **WHEN** `ART_SD_OUTPUT_FORMAT=webp` and `ART_SD_OUTPUT_QUALITY=60` and a
  valid PNG is encoded
- **THEN** the returned bytes start with the WebP RIFF/WEBP magic, decode to
  the same dimensions, carry extension `.webp`, and the same conversion at
  quality 100 on noisy content yields a larger encoding than at 60

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

#### Scenario: Corrupted transport bytes fail with the named code
- **WHEN** `encode` receives bytes that are not a decodable PNG
- **THEN** it raises `SDError` with code `sd_format_error` and nothing is
  written to the store

### Requirement: Generation metadata is embedded when preserved and provably absent when not
When `ART_SD_PRESERVE_GENERATION_METADATA` is true, the encoded output SHALL
carry the A1111-shaped generation-parameters text (prompt, negative prompt,
steps, CFG scale, sampler, scheduler, width, height, and — when the record
carries one — the seed, plus the configured checkpoint when set) in the
format-native location: PNG `tEXt` key `parameters`; JPEG, WebP, and AVIF
EXIF `UserComment`. The text SHALL be regenerated from engine-known values,
never copied wholesale from server-supplied chunks. When the setting is
false, the delivered artifact SHALL carry no generation metadata at all: PNG
output SHALL be re-saved with zero text chunks, and JPEG/WebP/AVIF output
SHALL be encoded without EXIF or ICC. Verification is format-aware metadata
inspection — every PNG ancillary chunk type parsed (no `tEXt`, `zTXt`,
`iTXt`, `eXIf`, or `iCCP`), JPEG APP-segments and WebP RIFF chunks parsed
(no EXIF, XMP, or ICC payload), AVIF `Image.info` free of `exif`/`xmp`/ICC —
and the original server parameter text asserted absent — never byte-marker
scanning alone.

#### Scenario: Preserved metadata round-trips from the encoded artifact
- **WHEN** metadata preservation is on and a png, webp, jpeg, or avif image
  is encoded and written
- **THEN** reading the stored file back yields the generation-parameters text
  containing the prompt and the recorded seed (PNG via the `parameters` text
  chunk; JPEG, WebP, and AVIF via the EXIF `UserComment` parsed with piexif)

#### Scenario: Stripping guarantees absence
- **WHEN** `ART_SD_PRESERVE_GENERATION_METADATA=false` and each of png, webp,
  jpeg, avif is encoded from an input PNG carrying `tEXt`, `iTXt`, EXIF, and
  ICC fixtures
- **THEN** none of the four outputs carries any metadata chunk, EXIF/XMP/ICC
  payload, or the original parameter text

#### Scenario: A seedless record fabricates no seed
- **WHEN** metadata preservation is on and the generated image's seed is
  `None`
- **THEN** the parameters text omits the seed entry entirely
