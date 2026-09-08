## MODIFIED Requirements

### Requirement: Roster portraits resolve through the named-portrait subject mechanism
Each roster row's portrait SHALL be resolved through the same named-portrait resolution the art
panel's portrait catalog uses: an explicit named `portrait_policy` on the character, the
canonical-age eligibility check, and the resolved asset or its placeholder. A row SHALL carry the same portrait
field vocabulary the art panel's catalog entries carry — the subject key, the asset status, the
same-origin media URL, the aspect ratio, the alt text, the placeholder descriptor, and the normalized face rectangle (a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` when the row carries a URL, and `null` when it carries a placeholder) — so the
client renders roster portraits through its existing portrait treatment rather than a second
vocabulary. Resolution SHALL NOT require the character to be present in the rendering actor's
current room. A character carrying no named portrait policy — which every character still pending
creation does, because the policy is established only at activation — SHALL resolve to the
no-portrait placeholder with no URL and no subject key.

#### Scenario: An activated character resolves its generated portrait
- **WHEN** a roster row is built for an activated character whose portrait asset is complete
- **THEN** the row carries that portrait's subject key, done status, and same-origin media URL,
  regardless of which room the character is standing in

#### Scenario: A pending character resolves to the no-portrait placeholder
- **WHEN** a roster row is built for a character still pending creation
- **THEN** the row carries the no-portrait placeholder with a null URL and a null subject key

#### Scenario: A not-yet-generated portrait resolves to its pending placeholder
- **WHEN** a roster row is built for an activated character whose portrait asset has not been
  generated yet
- **THEN** the row carries the placeholder descriptor and the asset's pending status rather than
  a URL

#### Scenario: A resolved roster row carries its face rectangle
- **WHEN** a roster row is built for an activated character that resolves to an image
- **THEN** the row carries the media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder roster row carries a null face rectangle
- **WHEN** a roster row resolves to any truthful placeholder
- **THEN** the row carries a null URL and a null face rectangle
