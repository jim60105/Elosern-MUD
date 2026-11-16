## MODIFIED Requirements

### Requirement: Generated art is converted locally to the configured output format at the configured quality
Encoding SHALL convert validated transport PNG bytes into the configured png/webp/jpeg/avif format at configured quality. Invalid input SHALL raise sd_format_error before publication. Gallery outputs SHALL use immutable per-image identities with that format extension; replacement SHALL leave earlier referenced card bytes intact.

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

#### Scenario: Format changes publish a distinct card
- **WHEN** a capped gallery regenerates from PNG storage to WebP
- **THEN** the replacement uses its fresh image identity and new extension; only the displaced unreferenced card file is cleaned after commit
