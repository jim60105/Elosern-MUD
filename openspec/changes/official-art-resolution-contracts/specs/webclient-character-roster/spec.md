## MODIFIED Requirements

### Requirement: Roster portraits resolve through the named-portrait subject mechanism
Each roster row's portrait SHALL be resolved through the same named-portrait resolution the art
panel's portrait catalog uses: an explicit named `portrait_policy` on the character, the
canonical-age eligibility check, and the resolved asset or its placeholder. A row SHALL carry the same portrait
field vocabulary the art panel's catalog entries carry — the subject key, the asset status, the
same-origin media URL, the aspect ratio, the alt text, the placeholder descriptor, the normalized
face rectangle (a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` when the row carries a URL, and
`null` when it carries a placeholder), and the server-authored portrait origin discriminator (see the
`official-art-resolution` capability) on every row that carries a media value — so the
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

#### Scenario: An official-resolved roster portrait names its origin
- **WHEN** a roster row's portrait resolves to an official read-only image through the presentation chain
- **THEN** the row carries the official-origin discriminator beside its media URL and the subject's own generation state remains untouched

### Requirement: Each roster row reports only canonical, owned character facts
Each row of the `roster` panel SHALL correspond to exactly one character in the authenticated
session puppet's owning account's character list, and SHALL carry that character's stable numeric
identity, current object key, current marker, creation-pending marker and portrait resolution.
Normally `current` SHALL identify the live owned puppet. While possessing a bound companion, it
SHALL identify the owning player character A whose body/portrait remains in the lineup, not the
controlled NPC B; B SHALL NOT be added to the account roster. The live party owner and canonical
`possessed_by` binding SHALL agree, and A SHALL still be verified against that same account's
character list. A missing, stale, unbound or foreign owner SHALL produce the existing unavailable
form, never select a different account from the NPC's back-reference. `pending` SHALL remain each
owned character's own creation marker, unchanged by possession.

Rows SHALL be ordered by ascending numeric identity so the presented order never depends on
handler iteration order, and the current owned character SHALL NOT be reordered to the front — it
is identified by its own field. The row count SHALL be bounded by a presenter-owned constant
independent of configured capacity, preserving the current owned character within that bound.
The panel SHALL carry no per-character resources, location, condition or last-played field: a row
states who the character is, not how they are doing. The panel SHALL NOT synthesize a display label
for a character whose key is ambiguous; pending is the disambiguating fact, and its presentation
belongs to the client. Portrait resolution and the roster wire shape SHALL remain read-only and
unchanged, except that the portrait vocabulary additionally carries the server-authored origin
discriminator the `official-art-resolution` capability adds on the row (one bounded enum field on
the portrait object; the row's own facts and every other field stay exactly as they are).

#### Scenario: Rows name the account's characters in identity order
- **WHEN** an account owns three characters and a snapshot is built for one of them
- **THEN** the roster carries three identity-ordered rows and exactly one current owned character

#### Scenario: A pending sibling appears as a pending row
- **WHEN** an account owns one activated character and one character pending creation
- **THEN** both appear, and only the pending character carries the pending marker

#### Scenario: The roster states nothing about a character's condition
- **WHEN** a row's character has low health, another location or a status condition
- **THEN** the row carries no resource, location or condition field

#### Scenario: A foreign character never appears
- **WHEN** a character outside the authenticated session's account exists
- **THEN** it appears in no roster row, including through a possessed NPC's owner back-reference

#### Scenario: Possession preserves A's current roster portrait
- **WHEN** A possesses bound companion B and the session puppet changes to B
- **THEN** the roster stays available from that session's account, A remains its sole current row with byte-identical portrait and pending fields, B is not a roster row, and release restores the same roster
