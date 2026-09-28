## MODIFIED Requirements

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The default drawer variant of the `World/ReferenceArtwork` component SHALL render a portrait catalog entry as one cover-fitted image
whose crop follows the entry's `face_rect`, with no invented frame: a `null` entry or a placeholder
entry (null URL) SHALL render the truthfully labelled placeholder and no image element; a media load
that fails SHALL degrade that frame to the labelled placeholder; and a subsequent entry whose URL
differs SHALL re-attempt and render the new image, so a repaired asset recovers without remounting the
surface. The component SHALL be manifest-listed in the re-frozen required set and covered by the
deterministic component-coverage gate.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** the default drawer frame receives an entry carrying a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: A placeholder entry renders no image
- **WHEN** the frame receives a null entry or an entry whose URL is null with a placeholder label
- **THEN** no image element exists in the frame and the placeholder's label is the rendered text

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** a rendered entry's image fires a load error, and the frame is later given an entry with a different URL
- **THEN** the failed load replaces the image with the labelled placeholder, and the changed URL renders a new image element carrying the replacement URL
