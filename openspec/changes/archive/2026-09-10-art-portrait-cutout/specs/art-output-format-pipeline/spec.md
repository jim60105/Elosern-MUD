## ADDED Requirements

### Requirement: An alpha channel survives every alpha-capable output format

`world/art/formats.py::encode(...)` SHALL preserve the alpha channel of an RGBA transport
PNG end to end for each of the three alpha-capable output formats — `png`, `webp`, and
`avif` — so a transparent-background artifact produced upstream is still transparent after
it is stored. Decoding the encoded bytes SHALL yield an image whose mode carries alpha and
whose fully transparent source pixels are still fully transparent, in both metadata modes
(`ART_SD_PRESERVE_GENERATION_METADATA` true and false), because the encoder's sanitizing
pixel copy SHALL copy the source mode rather than flattening it. The existing `jpeg`
behavior is unchanged: JPEG accepts no alpha and continues to be encoded from an RGB view,
which is why the `art-portrait-cutout` capability refuses the `jpeg` + background-removal
combination at settings import rather than allowing a silent flatten.

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
