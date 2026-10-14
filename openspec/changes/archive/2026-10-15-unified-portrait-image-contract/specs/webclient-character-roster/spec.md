# Spec Delta

## MODIFIED Requirements

### Requirement: Roster portraits resolve through the named-portrait subject mechanism
Owned roster portraits SHALL use the same complete canonical descriptor, eligibility and ordered source vocabulary as the art catalog, regardless of room presence. No field-copy omission SHALL discard terminal geometry or source faults. Roster schema 3 SHALL replace flat portrait image fields atomically across serializer, validators and all consumers.

#### Scenario: An activated character resolves its generated portrait
- **WHEN** a roster row is built for an activated character whose portrait asset is complete
- **THEN** the row carries that portrait's subject key, done status, and same-origin media URL,
  regardless of which room the character is standing in

#### Scenario: A pending character resolves to the no-portrait placeholder
- **WHEN** a roster row is built for a character still pending creation
- **THEN** the row carries the no-portrait placeholder with a null URL and a null subject key

#### Scenario: A not-yet-generated portrait resolves to its pending placeholder
- **WHEN** an activated owned character has no successful generated image yet
- **THEN** its descriptor truthfully states missing/pending generation and supplies applicable expected fallback without synthetic success

#### Scenario: A resolved roster row carries its face rectangle
- **WHEN** a roster row is built for an activated character that resolves to an image
- **THEN** the row carries the media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder roster row carries a null face rectangle
- **WHEN** an owned subject has no real image candidate
- **THEN** real geometry is absent and alpha-terminal geometry remains separate

#### Scenario: An official-resolved roster portrait names its origin
- **WHEN** a roster row's portrait resolves to an official read-only image through the presentation chain
- **THEN** the row carries the official-origin discriminator beside its media URL and the subject's own generation state remains untouched

#### Scenario: A roster row carries the catalog's portrait vocabulary
- **WHEN** an owned roster row is serialized
- **THEN** it carries the complete canonical descriptor, including independent generation state, ordered candidate/fault facts and alpha terminal, rather than a copied subset

#### Scenario: The face rectangle is normalized or null
- **WHEN** a roster portrait is serialized
- **THEN** each real candidate and alpha terminal carries its own bounded applicable geometry without merging them

#### Scenario: Every media-bearing row names its portrait origin
- **WHEN** a roster row carries a media value
- **THEN** it also carries the server-authored portrait origin discriminator (see the `official-art-resolution` capability)

#### Scenario: Only activation establishes a portrait policy
- **WHEN** a character still pending creation carries no named portrait policy, because the policy is established only at activation
- **THEN** its portrait resolves to the no-portrait placeholder with no URL and no subject key

### Requirement: Each roster row reports only canonical, owned character facts
Each row of the `roster` panel SHALL correspond to exactly one character in the authenticated
session puppet's owning account's character list, and SHALL carry that character's stable numeric
identity, current object key, current marker, creation-pending marker and portrait resolution.
Normally `current` SHALL identify the live owned puppet. Rows SHALL be ordered by ascending
numeric identity.

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

#### Scenario: Identity order never depends on handler iteration order
- **WHEN** the account's character list is presented
- **THEN** the presented order is fixed by ascending numeric identity and never depends on handler iteration order

#### Scenario: The current character is not reordered to the front
- **WHEN** the current owned character's numeric identity is not the smallest
- **THEN** it keeps its identity-ordered position and is identified as current by its own field rather than by position

#### Scenario: Possession keeps the owning character A current, not the NPC B
- **WHEN** A possesses bound companion B
- **THEN** `current` identifies the owning player character A whose body/portrait remains in the lineup, not the controlled NPC B, and B is not added to the account roster

#### Scenario: The possession owner must agree with the canonical binding
- **WHEN** the roster resolves a possessed session's owner
- **THEN** the live party owner and the canonical `possessed_by` binding agree, and A is still verified against that same account's character list

#### Scenario: A broken possession owner degrades the panel
- **WHEN** the possession owner is missing, stale, unbound or foreign
- **THEN** the panel produces the existing unavailable form and never selects a different account from the NPC's back-reference

#### Scenario: Possession leaves each pending marker alone
- **WHEN** a session is possessing a bound companion
- **THEN** `pending` remains each owned character's own creation marker, unchanged by possession

#### Scenario: Row count is bounded by a presenter-owned constant
- **WHEN** an account owns more characters than the presenter's bound
- **THEN** the row count stays within a presenter-owned constant independent of configured capacity, and the current owned character is preserved within that bound

#### Scenario: A row states who the character is, not how they are doing
- **WHEN** a roster row is built
- **THEN** it carries no last-played field, alongside the already-absent resource, location and condition fields

#### Scenario: An ambiguous key earns no synthesized label
- **WHEN** a character's key is ambiguous
- **THEN** the panel synthesizes no display label; pending is the disambiguating fact, and its presentation belongs to the client

#### Scenario: The wire shape stays unchanged apart from the origin discriminator
- **WHEN** roster portraits adopt canonical descriptors
- **THEN** only the portrait vocabulary and schema version change; identity/current/pending/capacity/lock facts, privacy and read-only semantics remain unchanged

