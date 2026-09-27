## ADDED Requirements

### Requirement: The built-in fallback images carry a transparent background
Each committed built-in fallback image SHALL be produced from the project art prompt library
through the same background-removal and encoding stages the portrait worker applies to generated
character and monster portraits, so each image carries an alpha channel in which the backdrop
around the figure is fully transparent and the figure itself is opaque and composes over any stage
or panel background without a visible rectangle or halo. The background SHALL have been removed
with a permissively licensed model, so the committed images carry no non-commercial licence
obligation. Each image SHALL keep its key, file name, and `.webp` extension, stay within the
declared size bound, and carry a face rectangle re-authored against its own pixels. A contract test
SHALL decode every committed default and fail when an image has no alpha channel, when any pixel
of its corner regions is not fully transparent, or when its central figure band is not opaque.

#### Scenario: Every default decodes with a transparent background
- **WHEN** the contract test decodes each committed fallback image
- **THEN** each image carries an alpha channel, every pixel in its four corner regions has alpha 0,
  and the mean alpha of its central figure band is at least 250 of 255

#### Scenario: An opaque default fails the contract
- **WHEN** a committed default without an alpha channel, or with an opaque corner, is placed in the
  defaults directory
- **THEN** the contract test fails naming that file

#### Scenario: The vocabulary and serving contract survive regeneration
- **WHEN** the regenerated images replace the opaque ones
- **THEN** the closed six-key vocabulary, the `.webp` extension, the size bound, and the per-key
  face-rectangle resolution all still hold, and each key serves the regenerated file under its
  unchanged name
