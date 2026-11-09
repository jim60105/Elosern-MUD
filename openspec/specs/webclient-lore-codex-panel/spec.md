## Purpose

The version-1 `lore_codex` presentation panel: the server-owned discovered-lore read
model (exact schema, discovered-only non-disclosure, canonical card rendering,
corrupt-record degradation, explicit fail-closed bounds, and push-on-discovery
timing) that the codex surface consumes.

## Requirements

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

### Requirement: Codex entry titles are the registry's display names

Each entry slot's `title` SHALL be the `display_name_zh` of its card, which every category declares as its first card field, so a race entry is titled by its race name (人類, never `human`) and a guild rank entry by its rank name (`F 級`). The entry `key` SHALL stay the opaque registry key.

#### Scenario: A race entry is titled by its display name
- **WHEN** a holder who discovered a race receives the panel
- **THEN** that entry's `title` equals the race's registry `display_name_zh`, its `key` is the opaque
  race key, and the key appears in no visible field value

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

A monster entry's `art` SHALL be the existing `portrait:monster:<species_key>` descriptor with its fallback terminal, or null for an unregistered visual key. A region or anchor entry's `art` SHALL be its declared scene archetype's scene descriptor, or null. Other entries' `art` SHALL be null. An art-building failure SHALL null that slot's art and be logged. Building art SHALL enqueue no job and write no record.

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

#### Scenario: An art failure degrades one slot only
- **WHEN** building one entry's art descriptor raises
- **THEN** that slot's `art` is null, the failure is logged through the observability facade, and the panel stays available with every other slot unchanged

### Requirement: The panel is bounded, trims placeholders then art, and fails closed

The panel SHALL declare and enforce bounds of 128 slots per category, 512 slots in total, 16 groups per category, 8 card fields, 1024 code points per field value and 8 variant lines, plus code-point bounds on every string. Over the envelope limit, trailing placeholders SHALL drop first, last category first, then entry art SHALL become null from the last slot backwards; counts stay untrimmed. If nothing is left to trim, the presenter SHALL raise its named error.

#### Scenario: Trailing placeholders drop first
- **WHEN** a synthetic codex exceeds the envelope limit by less than its placeholders weigh
- **THEN** only placeholders are dropped, last category first and last slot first, every entry slot is kept, each category's `total` is unchanged, and the payload fits the envelope

#### Scenario: Art is dropped after placeholders
- **WHEN** a synthetic codex still exceeds the envelope after every placeholder was dropped
- **THEN** entry slots lose their `art` (set to null) from the last slot backwards until the payload fits, and every entry slot and card is kept

#### Scenario: An oversize codex without placeholders or art fails closed
- **WHEN** a codex whose entry cards alone exceed the envelope is built
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

### Requirement: The handbook codex tab renders the committed panel as a grouped tile wall

The codex tab SHALL render only the committed `lore_codex` panel. Its rail SHALL carry one entry per shipped category, in panel order, with the category's `discovered` count. The wall SHALL render the selected category's groups in order, with a group heading for each non-null label, and one tile per slot in slot order. Navigation SHALL be local and dispatch nothing.

#### Scenario: Selecting a category shows its wall
- **WHEN** the player selects a rail entry
- **THEN** the wall shows exactly that category's slots grouped as shipped, and no request is dispatched

#### Scenario: Placeholders are focusable but not selectable
- **WHEN** focus reaches a placeholder tile and the player presses Enter or clicks it
- **THEN** the tile carries an accessible name that names no entry and `aria-disabled`, and the selection does not change

#### Scenario: Tiles walk by keyboard
- **WHEN** focus is on a tile and the player presses an arrow key, Home or End, then Enter on an entry tile
- **THEN** focus moves in reading order across groups without changing the selection, and Enter selects the focused entry

#### Scenario: The detail renders the card verbatim
- **WHEN** an entry tile is selected
- **THEN** the detail shows the slot's title and every card field other than the title field, in panel order, each value verbatim under a readable field name, and no raw field identifier is visible

#### Scenario: The selection is remembered per category
- **WHEN** the player selects an entry, switches category, and returns
- **THEN** the same entry is selected again within the same memory scope

#### Scenario: A codex route request opens the codex tab
- **WHEN** the handbook route entry is called with the codex tab, in exploration and in combat
- **THEN** the quest drawer opens with the codex tab selected

### Requirement: Monster research stages differ by shape and are explained

A monster entry tile SHALL mark its stage by a shape that differs between `defeated` and `sighted`, and a placeholder SHALL use a third mark. The monster wall SHALL carry a legend naming all three marks. The legend SHALL stay visible at the bottom edge of the wall while the tiles scroll. The monster detail SHALL show a two-step research track whose steps reflect the stage.

#### Scenario: Stage marks differ by shape
- **WHEN** the monster wall shows a defeated tile, a sighted tile and a placeholder
- **THEN** each carries a distinct stage-mark element (`data-stage` `defeated`, `sighted`, or `unknown`) whose shape differs, not only its colour

#### Scenario: The legend stays pinned
- **WHEN** the monster wall's tiles overflow and the wall is scrolled to its top and then to its bottom
- **THEN** the legend's box lies inside the wall's visible box at both positions

#### Scenario: The research track follows the stage
- **WHEN** a sighted and then a defeated monster entry is selected
- **THEN** the track marks only its first step reached for the sighted entry, and both steps for the defeated entry; for the sighted entry the second step names exactly the readable names of its `locked_fields`

### Requirement: A sighted monster shows its locked fields without values

For each name in a selected entry's `locked_fields`, the detail SHALL render one locked box labelled with that field's readable name. A locked box SHALL show no value. A defeated entry SHALL render no locked box.

#### Scenario: Locked fields render as locked boxes
- **WHEN** a sighted entry whose `locked_fields` names four fields is selected
- **THEN** the detail renders four locked boxes in `locked_fields` order and no value for those fields

#### Scenario: A defeated entry has no locked box
- **WHEN** a defeated entry is selected
- **THEN** no locked box renders

### Requirement: Codex hero art falls back to the category emblem

The detail hero SHALL render the selected entry's `art` descriptor through the shared artwork attempt lifecycle. When `art` is null, when no attempt or terminal of the descriptor has loaded, or when every permitted source failed, the hero SHALL render the category emblem instead. The hero SHALL never show an empty frame.

#### Scenario: A null art shows the emblem
- **WHEN** an entry whose `art` is null is selected
- **THEN** the hero shows that category's emblem

#### Scenario: A failed image falls back to the emblem
- **WHEN** an entry's art descriptor has one attempt whose image fails to load and no terminal
- **THEN** after the failure the hero shows the category emblem and no image frame

#### Scenario: A loaded image replaces the emblem
- **WHEN** an entry's art descriptor attempt loads successfully
- **THEN** the hero shows that image

### Requirement: The handbook codex tab degrades honestly

Before the first `lore_codex` commit the codex tab SHALL be enabled and show the shared empty state. While the panel is unavailable the tab SHALL be disabled, yet focusable, with the panel's reason. A codex with nothing discovered SHALL render its full placeholder wall and the empty detail guidance. A selection gone after a commit SHALL move to the category's first entry, else to the empty detail.

#### Scenario: Before the first commit
- **WHEN** the codex tab is selected before any `lore_codex` panel was committed
- **THEN** it shows the shared empty state and no tile

#### Scenario: An unavailable panel disables the tab
- **WHEN** the committed `lore_codex` panel is the common unavailable form
- **THEN** the codex tab is disabled, keyboard focus can reach it, and its tooltip and accessible description carry the panel's reason message

#### Scenario: Nothing discovered shows the placeholder wall
- **WHEN** the committed panel holds only placeholders
- **THEN** the wall renders every placeholder and the detail renders the shared empty guidance

#### Scenario: A vanished selection falls back
- **WHEN** the selected entry is gone after a commit
- **THEN** the category's first entry is selected, or the empty detail shows when it has none

### Requirement: The handbook codex tab fits the reference viewports

On the live client at 1451x790 and at 2560x1440 the codex tab SHALL lay out its rail, wall and detail columns side by side inside the drawer body. The wall SHALL NOT scroll horizontally. No rendered text SHALL be smaller than the `--text-xs` token's computed size. Each legend mark SHALL have a fixed size that does not depend on the wall width.

#### Scenario: Three columns fit at both viewports
- **WHEN** the live client opens the monster category of the codex tab at 1451x790 and at 2560x1440
- **THEN** the rail, wall and detail columns do not overlap, each lies inside the drawer body, and the wall has no horizontal scroll overflow

#### Scenario: No text below the floor
- **WHEN** the codex tab renders at either viewport
- **THEN** every visible text node's computed font size is at least the computed size of `--text-xs`

#### Scenario: Legend marks keep their size
- **WHEN** the monster legend renders at both viewports
- **THEN** each legend mark's rendered width equals `12px` times the page's `--ui-scale` within 1px
