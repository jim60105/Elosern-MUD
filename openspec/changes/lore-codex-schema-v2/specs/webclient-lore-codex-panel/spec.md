## REMOVED Requirements

### Requirement: The lore codex panel is an exact read-only version-1 presentation panel

**Reason**: Replaced by the version-2 schema requirement. The panel now carries totals, groups and slots (design §4.2).

**Migration**: None (pre-release). The server and client validators accept only version 2.

### Requirement: The panel discloses only what the holder discovered

**Reason**: Design D4 amends non-disclosure from "discloses no existence" to "discloses only count and ordinal position". The replacement requirement is "The panel discloses only the count and ordinal position of undiscovered entries".

**Migration**: None.

### Requirement: The panel is bounded and fails closed on registry growth

**Reason**: Replaced by "The panel is bounded, trims only placeholders, and fails closed", which carries the v2 slot bounds and the placeholder-first envelope trimming.

**Migration**: None.

## MODIFIED Requirements

### Requirement: Cards are rendered by the canonical renderer, never composed by the presenter

Each entry's `card` SHALL be exactly the canonical renderer's output: `species_card(key, stage)` for a monster entry and `lore_card(category, key)` for every other category, in declared field order. The presenter SHALL NOT add, remove, reorder, reword or truncate a field. A recorded entry whose key no longer resolves in its registry SHALL produce no slot, and the omission SHALL NOT make the panel unavailable.

#### Scenario: A card matches the renderer exactly
- **WHEN** an entry is serialized
- **THEN** its card fields and their order equal the canonical renderer's output for that category, key and stage

#### Scenario: An entry whose registry key vanished is omitted
- **WHEN** the holder's record names an entry absent from its category's registry
- **THEN** that entry produces neither an entry slot nor a placeholder, the rest of the codex ships normally, and the stored record is not rewritten

#### Scenario: A malformed identifier is corruption, not a vanished key
- **WHEN** the holder's record holds an identifier such as `race:` or `race:elf:extra`
- **THEN** the reader treats it as a corrupt record and the whole panel degrades; it is not omitted from an otherwise-available payload

#### Scenario: A malformed identifier is rejected before presentation
- **WHEN** the holder's record holds a malformed identifier — empty category or key, or a key
  carrying extra delimiters
- **THEN** the reader rejects it as a corrupt record rather than hand it to the presenter for
  omission, because it is corruption, not a vanished key

### Requirement: Codex entry titles are the registry's display names

Each entry slot's `title` SHALL be the `display_name_zh` of its card, which every category declares as its first card field, so a race entry is titled by its race name (人類, never `human`) and a guild rank entry by its rank name (`F 級`). The entry `key` SHALL stay the opaque registry key.

#### Scenario: A race entry is titled by its display name
- **WHEN** a holder who discovered a race receives the panel
- **THEN** that entry's `title` equals the race's registry `display_name_zh`, its `key` is the opaque
  race key, and the key appears in no visible field value

## ADDED Requirements

### Requirement: The lore codex panel is an exact read-only version-2 presentation panel

The registry SHALL register `lore_codex` at schema version 2. Its available form SHALL contain exactly `schema_version`, `available`, `discovered_total`, `total` and `categories`, with the eight categories in `CODE_CATEGORIES` order. A category SHALL contain exactly `key`, `label`, `discovered`, `total` and `groups`. A group SHALL contain exactly `key`, `label` and `slots`. Slots SHALL keep registry order. Building the panel SHALL mutate no state.

#### Scenario: A codex with two discoveries serializes exactly
- **WHEN** a holder who discovered one synthetic race and one synthetic anchor receives the panel
- **THEN** every category carries one slot per registry entry in registry order, the race and anchor slots are entry slots with rendered cards, every other slot is a placeholder, and `discovered_total` is 2

#### Scenario: An empty codex is available
- **WHEN** a holder who discovered nothing receives the panel
- **THEN** the panel is available, every slot is a placeholder, every `discovered` is 0 and `discovered_total` is 0

#### Scenario: Totals count the registry
- **WHEN** the panel serializes untrimmed
- **THEN** each category's `total` equals its registry size and its slot count, `discovered` equals its entry-slot count, and the top-level values are the sums

#### Scenario: A non-monster category has one unlabeled group
- **WHEN** any category other than monster serializes
- **THEN** it carries exactly one group whose `label` is null

#### Scenario: The presenter reveals nothing
- **WHEN** the panel is built twice in a row for the same holder
- **THEN** `db.lore_discovered` and `db.lore_species_defeated` are unchanged and both serializations are identical

#### Scenario: Legal registry entries survive validation
- **WHEN** a holder discovered any entry that resolves in its registry and fits the bounds
- **THEN** the server and client validators accept the payload and preserve the opaque key without normalization

### Requirement: The monster category groups species by threat tier

The monster category SHALL group its slots by the threat tier of each species' default variant. Groups SHALL follow `MONSTER_TIER_REGISTRY` order, and only tiers holding at least one species SHALL appear. A group's `key` SHALL be the tier key and its `label` the tier's display name. Each species' slot, entry or placeholder, SHALL sit in its tier's group.

#### Scenario: Species fall into their tiers in tier order
- **WHEN** synthetic species of two tiers are registered and the holder sighted one of them
- **THEN** the monster category carries the two tier groups in tier registry order, each holding its species' slots in species registry order

#### Scenario: An empty tier has no group
- **WHEN** a registered tier is the default tier of no species
- **THEN** no group with that tier key appears

### Requirement: The panel discloses only the count and ordinal position of undiscovered entries

An undiscovered registry entry SHALL be serialized as exactly `{placeholder: true}` at its ordinal position within its group. The panel SHALL NOT ship any key, title, art, stage, field name or other value that could identify it. The only facts disclosed about undiscovered entries SHALL be their counts and their positions within groups.

#### Scenario: A placeholder carries no identity
- **WHEN** a holder discovered one of three entries in a category
- **THEN** the other two slots are exactly `{"placeholder": true}`, and no registry key or display name of an undiscovered entry occurs anywhere in the serialized payload

#### Scenario: The client rejects an identifying placeholder
- **WHEN** a payload whose placeholder carries any field besides `placeholder` reaches the client validator
- **THEN** the client rejects it rather than rendering it

### Requirement: Monster entries carry stage-gated cards

A monster entry's `stage` SHALL be `defeated` when the holder's defeated record holds the species, else `sighted`. Every other category's `stage` SHALL be null. A sighted card SHALL carry only the sighted-stage fields, and `locked_fields` SHALL name exactly the defeated-stage fields it omits. A defeated card SHALL carry every field, with empty `locked_fields`. `author_hidden_truth_zh`, `author_explanation_zh` and `author_conjecture_zh` SHALL never be serialized.

#### Scenario: A sighted species withholds its defeated fields
- **WHEN** a holder sighted but never defeated a synthetic species
- **THEN** its card names exactly `display_name_zh`, `published_appearance_zh` and `threat_tier`, and its `locked_fields` is exactly `published_description_zh`, `published_ecology_zh`, `habitat_tags` and `variants`, with none of their values present in the payload

#### Scenario: A defeated species shows every field
- **WHEN** the holder defeated that species
- **THEN** its stage is `defeated`, its card carries all seven fields in order, and `locked_fields` is empty

#### Scenario: Only ordinary variants are listed
- **WHEN** a defeated species has one ordinary and one stronger variant
- **THEN** its `variants` value lists only the ordinary variant

#### Scenario: Author-private text never ships
- **WHEN** the panel is built for a holder who defeated a synthetic species whose author-private fields carry marker text
- **THEN** no marker text occurs anywhere in the serialized payload at either stage

#### Scenario: Non-monster entries carry no stage
- **WHEN** any non-monster entry serializes
- **THEN** its `stage` is null and its `locked_fields` is empty

### Requirement: Codex entries carry an existing art descriptor or none

A monster entry's `art` SHALL be the existing portrait descriptor of the `portrait:monster:<species_key>` subject, including its fallback terminal, or null when the species is not a registered visual key. A region or anchor entry's `art` SHALL be the existing scene descriptor of its declared scene archetype, or null when it declares none. Every other entry's `art` SHALL be null. Building art SHALL enqueue no job and write no record.

#### Scenario: A monster entry uses the monster portrait subject
- **WHEN** a sighted synthetic species is a registered visual key
- **THEN** its `art` is a descriptor that the shared artwork validator accepts, for that species' monster portrait subject

#### Scenario: A region entry uses its scene archetype
- **WHEN** a discovered region declares a registered scene archetype
- **THEN** its `art` is a scene descriptor for that archetype that the shared artwork validator accepts

#### Scenario: Other categories carry no art
- **WHEN** a race, nation, element, magic or guild entry serializes
- **THEN** its `art` is null

#### Scenario: Art building is read-only
- **WHEN** the panel is built for a holder with discovered monsters and regions
- **THEN** no art job is enqueued and no art record is created

### Requirement: The panel is bounded, trims only placeholders, and fails closed

The panel SHALL declare and enforce bounds of 128 slots per category, 512 slots in total, 16 groups per category, 8 card fields, 1024 code points per field value and 8 variant lines, plus code-point bounds on every string. If the payload exceeds the envelope limit, trailing placeholders SHALL be dropped first, from the last category backwards, while `discovered` and `total` keep the untrimmed counts. If no placeholder is left to drop, the presenter SHALL raise its named error.

#### Scenario: Trailing placeholders drop first
- **WHEN** a synthetic codex exceeds the envelope limit by less than its placeholders weigh
- **THEN** only placeholders are dropped, last category first and last slot first, every entry slot is kept, each category's `total` is unchanged, and the payload fits the envelope

#### Scenario: An oversize codex without placeholders fails closed
- **WHEN** a codex whose entry slots alone exceed the envelope is built
- **THEN** the presenter raises its named validation error and ships nothing

#### Scenario: A bound violation raises
- **WHEN** a category would exceed 128 slots or a card would exceed 8 fields
- **THEN** the presenter raises its named validation error

#### Scenario: The client mirror rejects a payload the server would not emit
- **WHEN** a payload with a ninth category, a reordered category list, a slot count above `total`, a `discovered` that differs from the entry-slot count, or an extra slot field reaches the client validator
- **THEN** the client rejects it

#### Scenario: The client validator mirrors the declared bounds
- **WHEN** the server declares its payload bounds
- **THEN** the client validator mirrors the exact values, guarded by the dual-direction parity contract
