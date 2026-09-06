# Delta spec: webclient-lore-codex-panel (webclient-lore-codex-panel)

## ADDED Requirements

### Requirement: The lore codex panel is an exact read-only version-1 presentation panel

The presentation registry SHALL register a `lore_codex` panel at schema version 1. Its available form
SHALL contain exactly `schema_version`, `available`, `categories`, and `discovered_total`, and the
registered common unavailable form SHALL keep the shared field set, reason, and semantics.

`categories` SHALL be the eight codex categories in `CODE_CATEGORIES` mapping order — never a
subset and never reordered — each containing exactly `key`, `label`, `count`, and `entries`. `label`
SHALL be the player-facing category name. `count` SHALL equal the length of that category's
`entries`. Each entry SHALL contain exactly `key`, `title`, and `card`, where `card` is an ordered
list of that category's declared card fields rendered through the canonical `lore_card` renderer,
each field carrying exactly `name` and `value`. `discovered_total` SHALL equal the sum of the
category counts.

The presenter SHALL be read-only: it SHALL NOT mutate the discovered record, reveal an entry, or
touch any other state, and SHALL emit no live object or filesystem reference.

#### Scenario: A codex with two discoveries serializes exactly
- **WHEN** a puppeted holder who has discovered one race and one anchor receives a full snapshot
- **THEN** the payload carries all eight categories in mapping order, the race and anchor groups each
  carry one entry with its rendered card, every other group carries `count` 0 and `entries` `[]`, and
  `discovered_total` is 2

#### Scenario: An empty codex is available, not unavailable
- **WHEN** a holder who has discovered nothing receives a snapshot
- **THEN** the panel is available, all eight groups carry `count` 0 and `entries` `[]`, and
  `discovered_total` is 0

#### Scenario: The presenter reveals nothing
- **WHEN** the panel is built twice in a row for the same holder
- **THEN** `db.lore_discovered` is byte-for-byte unchanged and both serializations are identical

### Requirement: The panel discloses only what the holder discovered

An entry SHALL appear only when the holder's record contains its namespaced identifier. The panel
SHALL NOT ship an undiscovered entry, SHALL NOT ship a count, total, ratio, or placeholder that
reveals how many entries a category could hold, and SHALL NOT ship a locked, hidden, or greyed entry
stub. A category with nothing discovered SHALL ship as an empty group carrying only its key, its
label, `count` 0, and an empty entry list — the same non-disclosure rule the `lore` command enforces
by returning one fixed not-found line for unknown categories, unknown keys, and undiscovered entries
alike.

#### Scenario: An undiscovered entry is absent entirely
- **WHEN** a holder has discovered one of several registered entries in a category
- **THEN** only that entry appears, and nothing in the payload indicates that others exist

#### Scenario: Registry size never leaks
- **WHEN** the payload for any holder is inspected
- **THEN** it contains no registry total, no denominator, no completion ratio, and no placeholder
  entry

### Requirement: Cards are rendered by the canonical renderer, never composed by the presenter

Each entry's `card` SHALL be exactly what `lore_card(category, key)` returns for that entry, in the
category's declared field order, with no field added, removed, reordered, reworded, or truncated
mid-value by the presenter. An entry present in the holder's record whose key no longer resolves in
its registry SHALL be omitted from the payload rather than shipped with a fabricated card, and the
omission SHALL NOT make the panel unavailable.

#### Scenario: A card matches the renderer exactly
- **WHEN** an entry is serialized
- **THEN** its card fields and their order equal `lore_card` output for that category and key

#### Scenario: An entry whose registry key vanished is omitted
- **WHEN** the holder's record names an entry absent from its category's registry
- **THEN** that entry is omitted, the rest of the codex ships normally, and the stored record is not
  rewritten

### Requirement: The lore codex panel is host-independent

The panel SHALL be built without resolving any service host, registration, schedule, or room. Its
availability SHALL depend only on the holder being a puppeted character whose discovered record can
be read, so the codex is readable anywhere the player stands.

#### Scenario: The codex is readable in the wilderness
- **WHEN** a holder with discoveries stands in a room with no NPC present
- **THEN** the panel is available and carries every discovered entry

### Requirement: A corrupt codex record degrades the whole panel and repairs nothing

A `LoreRecordError` from the reader SHALL make the WHOLE panel degrade to the registry-owned common
unavailable form. The panel SHALL NOT ship the entries that happened to parse, and SHALL NOT reset,
rewrite, or repair the stored record.

#### Scenario: A malformed record hides the whole panel
- **WHEN** a holder's `db.lore_discovered` holds malformed data
- **THEN** the panel is the common unavailable form and no entry is shipped

#### Scenario: Degradation never repairs the stored record
- **WHEN** the panel degrades on a corrupt record
- **THEN** `db.lore_discovered` is byte-for-byte unchanged

### Requirement: The panel is bounded and fails closed on registry growth

The panel SHALL declare explicit bounds: a maximum entry count per category, a maximum total entry
count, a maximum card-field count per entry, and code-point bounds on every string. It SHALL close
with the shared `MAX_CANONICAL_JSON_BYTES` envelope guard and FAIL CLOSED rather than truncating or
paginating, so growth in an underlying lore registry surfaces as a loud test failure that forces a
deliberate decision rather than a silently clipped codex. The client-side validator SHALL mirror
these exact bounds, guarded by the existing dual-direction parity test.

#### Scenario: Exceeding a bound raises rather than truncating
- **WHEN** a holder's discoveries would produce a payload exceeding a declared bound or the envelope
  limit
- **THEN** the presenter raises its named validation error and ships nothing truncated

#### Scenario: The client mirror rejects a payload the server would not emit
- **WHEN** a payload with a ninth category, a reordered category list, an extra entry field, or an
  extra card-field key reaches the client validator
- **THEN** the client rejects it rather than rendering it

### Requirement: The panel is pushed when a discovery lands

The coordinator SHALL mark the panel dirty and push it whenever the sole writer records a new reveal,
so a discovery made during play reaches an open codex surface without a reconnect. A repeat reveal,
which the writer treats as a no-op, SHALL NOT push.

#### Scenario: A new discovery refreshes the codex
- **WHEN** an entry the holder did not have is revealed
- **THEN** the `lore_codex` panel is pushed carrying the new entry

#### Scenario: A repeat reveal pushes nothing
- **WHEN** an already-discovered entry is revealed again
- **THEN** no push occurs
