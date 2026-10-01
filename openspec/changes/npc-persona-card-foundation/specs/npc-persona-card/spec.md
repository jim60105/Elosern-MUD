## Purpose

Define the compact NPC character card every NPC carries, the plain-text and render-budget rules that guarantee the dialogue prompt never truncates it, and the deterministic persistence and versioning of each NPC's effective card.

## ADDED Requirements

### Requirement: A compact NPC card has exactly seven fields of fixed shape
A compact NPC card SHALL be a mapping with exactly the top-level keys `identity`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, and `social_connection`. `identity` SHALL be a mapping with exactly the keys `public` and `hidden`; every other field SHALL be text. `identity.public`, `appearance`, `personality`, `speech_style`, `life_story`, and `habit` SHALL be required and non-empty after normalization; `identity.hidden` and `social_connection` MAY be empty and SHALL persist as empty strings when cleared, never as absent keys or `null`. Any unknown key at either level, any missing key, and any non-text leaf (number, boolean, null, list, or nested object) SHALL be rejected with a stable reason naming the offending leaf. The card shape SHALL apply to NPC producers and the NPC author editor only; it SHALL NOT restrict the persona record of a player character or any other living entity.

#### Scenario: A complete card is accepted
- **WHEN** a card carrying all seven fields with non-empty required leaves and an empty `identity.hidden` and `social_connection` is validated
- **THEN** it is accepted and its normalized form keeps both optional leaves as empty strings

#### Scenario: An unknown key is rejected
- **WHEN** a card carries an extra top-level key such as `background`, or `identity` carries a key other than `public` and `hidden`
- **THEN** validation rejects it with the `unknown_field` reason naming that key and nothing is persisted

#### Scenario: A missing or empty required leaf is rejected
- **WHEN** a card omits `speech_style`, or its `personality` is whitespace only
- **THEN** validation rejects it with `missing_field` or `required_empty` naming that leaf

#### Scenario: A non-text leaf is rejected
- **WHEN** a card's `habit` is a number, boolean, null, or list
- **THEN** validation rejects it with `not_text` naming `habit`

#### Scenario: Player personas are not constrained
- **WHEN** a player character's persona record carries structured appearance or a `background` key
- **THEN** the player's persona reading, rendering, and editing behave exactly as before

### Requirement: Card text is normalized plain text
Every card leaf SHALL be normalized by converting CRLF and lone CR line endings to LF and trimming outer whitespace, keeping interior text verbatim. Card text SHALL never be interpreted as markup, a template, a command, or an executable instruction; every output surface SHALL escape it for that surface.

#### Scenario: Line endings and outer whitespace normalize
- **WHEN** a leaf is submitted as `"  第一行\r\n第二行\r  "`
- **THEN** its normalized value is `"第一行\n第二行"`

#### Scenario: Template-like text is kept literally
- **WHEN** a leaf contains `{name}` or markup-like characters
- **THEN** the normalized value keeps those characters literally and no substitution occurs

### Requirement: Card bounds count rendered labels and are never satisfied by truncation
Each text leaf SHALL be at most 600 Unicode code points after normalization, counting an astral character as one code point. The rendered identity section, including its `身分` header and the `公開身分`/`隱秘身分` line labels, SHALL be at most 600 code points. The complete labeled card block, including every label and line separator, SHALL be at most 2,000 code points. An over-bound card SHALL be rejected with `leaf_too_long` naming the leaf, `identity_section_too_long`, or `card_too_long`; it SHALL never be shortened. A card whose every leaf is at its individual maximum simultaneously is invalid under the total bound and SHALL be rejected.

#### Scenario: A 600-code-point leaf of astral characters passes
- **WHEN** a leaf holds exactly 600 astral characters and the rendered card stays within 2,000 code points
- **THEN** the card is accepted

#### Scenario: A 601-code-point leaf is rejected by name
- **WHEN** `life_story` holds 601 code points
- **THEN** validation rejects it with `leaf_too_long` naming `life_story`

#### Scenario: The identity section bound counts its labels
- **WHEN** `identity.public` and `identity.hidden` are each within 600 code points but the rendered identity section with labels exceeds 600
- **THEN** validation rejects it with `identity_section_too_long`

#### Scenario: The total bound counts labels and separators
- **WHEN** the raw leaf text totals under 2,000 code points but the rendered labeled block exceeds 2,000
- **THEN** validation rejects it with `card_too_long`

### Requirement: Validation and prompt rendering share one field order and label policy
The card SHALL render in the order identity, appearance, personality, speech_style, life_story, habit, social_connection, with `speech_style` labelled `說話風格` immediately after `personality`. An empty optional leaf SHALL contribute no section and no placeholder text. For every valid card, the block the card contract measures SHALL be byte-identical to the block the persona reader produces for that card, and SHALL contain no truncation marker.

#### Scenario: A valid card renders without truncation through the reader
- **WHEN** a valid card at the total boundary is stored on an entity and flattened over the card render order
- **THEN** the reader's block equals the contract's rendered block and contains no truncation marker

#### Scenario: Empty optional fields add nothing
- **WHEN** a valid card has empty `identity.hidden` and `social_connection`
- **THEN** the rendered block has no `隱秘身分` line and no `人脈` section

### Requirement: NPC persona metadata is a separate record
The effective card SHALL be stored only at the NPC's persona record. A separate NPC persona metadata record SHALL hold the card format version, the content-generation marker, a monotonic positive `persona_version`, and initialization provenance. Provenance SHALL be one of the closed kinds `profile`, `companion`, `import`, `generated_quest`, or `offline_bundle`, carrying identifiers only and never prose. Metadata SHALL never be stored inside the persona record and SHALL never be rendered into any prompt or look output.

#### Scenario: Metadata stays out of the persona record
- **WHEN** an NPC card is initialized from a profile
- **THEN** the persona record contains exactly the seven card fields, and the metadata record carries the format, generation, `persona_version` 1, and `{"kind": "profile", "profile": <key>}`

#### Scenario: Unknown provenance is rejected
- **WHEN** initialization is requested with a provenance kind outside the closed set or with a prose value
- **THEN** it is rejected before any write

### Requirement: Reading an NPC persona never initializes or repairs it
Reading an NPC's persona for an editor or any consumer SHALL never write. A non-NPC target, a missing card, missing metadata, or a stored card or metadata that fails validation SHALL yield an explicit unavailable result with a stable reason and an operational warning event, and SHALL leave the stored records unchanged.

#### Scenario: A corrupt card reads as unavailable without repair
- **WHEN** an NPC's stored persona record carries an unknown key
- **THEN** the read returns unavailable with the `corrupt_card` reason, emits the unavailable event, and the record is byte-identical afterwards

#### Scenario: An NPC without metadata reads as unavailable
- **WHEN** an NPC has a persona record but no metadata record
- **THEN** the read returns unavailable with the `missing_meta` reason and nothing is written

### Requirement: Initialization never overwrites a marked NPC
Initializing an NPC persona SHALL validate the card before writing and SHALL write the card and its metadata, with `persona_version` 1 and the current content-generation marker, in one atomic unit. Initializing an NPC that already carries metadata with the current content-generation marker SHALL leave its card and version unchanged and return the existing state. A rejected card SHALL write nothing.

#### Scenario: A first initialization writes card and metadata together
- **WHEN** a valid card is initialized on an NPC with no persona
- **THEN** the NPC carries the normalized card and metadata at version 1, and both are visible together after commit

#### Scenario: Re-initialization keeps the effective card
- **WHEN** an already-initialized NPC whose card was later edited to version 3 is initialized again from its original profile
- **THEN** its card and version 3 are unchanged

#### Scenario: An invalid card writes nothing
- **WHEN** initialization receives a card that fails validation
- **THEN** neither the persona record nor the metadata record is written

### Requirement: Persona updates are compare-and-set on persona_version
Every persona update SHALL compare the submitted expected version with the persisted version inside the same database transaction as the write, including for a submission whose card equals the stored card. A complete normalized card that differs from the stored card in any leaf, including either identity leaf, SHALL be written with `persona_version` incremented by exactly one in the same transaction. A card exactly equal to the stored normalized card SHALL succeed without advancing the version. A version mismatch SHALL reject without writing and report the current version. Changing a card and later changing it back SHALL advance the version twice. A boolean or non-integer expected version SHALL be rejected.

#### Scenario: A changed hidden identity advances the version
- **WHEN** an update at the current version changes only `identity.hidden`
- **THEN** the new card is stored and the version increases by one

#### Scenario: An identical card is a no-op success
- **WHEN** an update at the current version submits the stored card unchanged
- **THEN** the result is unchanged success and the version does not advance

#### Scenario: A stale version is rejected even for a no-op
- **WHEN** an update submits the stored card unchanged with an expected version one below the current version
- **THEN** it is rejected as a version conflict reporting the current version and nothing is written

#### Scenario: Change and revert advances twice
- **WHEN** a leaf is changed and then changed back by two successful updates
- **THEN** the version has advanced by two

### Requirement: Persona writes are atomic, serialized, and restore caches on rollback
Every NPC persona write SHALL validate before persistence, SHALL perform its version read and its card and metadata writes in one database transaction that is serialized against concurrent writers in other processes by a database-held lock rather than a read-then-assign, and on any failure SHALL restore the in-memory attribute cache of both records to their pre-write values before any other reader can observe them.

#### Scenario: A failure mid-write leaves no partial state
- **WHEN** the metadata write raises after the card write inside one update
- **THEN** the transaction rolls back, both the stored records and the attribute cache equal their prior values, and the exception propagates or is reported with its stable reason

#### Scenario: Two writers cannot both win the same version
- **WHEN** two updates submit the same expected version in sequence without re-reading
- **THEN** exactly one succeeds and the other is rejected as a version conflict

### Requirement: Persona writers emit commit-bound events without persona text
Initialization and update SHALL emit operational events through the observability facade only after commit, carrying the NPC identity, acting character when present, provenance kind and profile key when present, and old and new version. Expected rejections SHALL emit an informational event with a stable reason. No event SHALL carry any card text, hidden identity, or dialogue.

#### Scenario: An update logs versions, not prose
- **WHEN** an update succeeds
- **THEN** one `npc_persona_updated` event carries the NPC, the acting character, and the old and new versions, and no context value contains any card leaf text

#### Scenario: A rolled-back write logs no success event
- **WHEN** an enclosing transaction rolls back after an initialization
- **THEN** no `npc_persona_initialized` event is emitted
