## MODIFIED Requirements

### Requirement: The gallery panel is an exact read-only version-2 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 4,
available in exploration mode. Its available form SHALL be exactly the version-4
category-scoped shape: `schema_version`, `available`, `kind` (the literal `gallery`),
`categories`, `category`, `groups`, `selected`, `description`, `cards`,
`official_entries`, `equipment_summary`, `capabilities`, `binding_warnings`, and
`error_state`. The registered unavailable form SHALL keep the common field set,
reason, and semantics.

#### Scenario: An empty gallery is available, not unavailable

- **WHEN** a puppet whose character has no gallery record and no pending job receives a full snapshot
- **THEN** the `gallery` panel is available with category `mine`, `cards: []`, and the puppet named as `selected`

#### Scenario: The presenter mutates nothing

- **WHEN** the panel is built twice in a row for the same puppet
- **THEN** every `GalleryRecord`, card, gallery job record, official-art preference, and stored file is byte-for-byte unchanged and both serializations are identical

#### Scenario: Official entries appear without touching cards

- **WHEN** the selected subject's content reference resolves a catalog directory holding three admitted images, one of them the subject's retained personal selection
- **THEN** `official_entries` carries exactly three official rows with the personal selection marked `is_current`, `cards` still lists only the runtime rows, and no card row was added or removed

#### Scenario: No reference or empty catalog means no official rows

- **WHEN** the selected subject has no content reference, or the reference is absent from the snapshot
- **THEN** `official_entries` is an empty list, present and not null

#### Scenario: A malformed official row fails both validator sides

- **WHEN** an official row carries a URL outside the official fingerprint vocabulary, an extra key, or a rectangle outside `[0, 1]`
- **THEN** both the Python and the JavaScript validator reject the payload and the panel degrades to the renderer's recovery path

#### Scenario: Panel building reads only

- **WHEN** the panel is built
- **THEN** it creates, mutates, and deletes no `GalleryRecord`, card, gallery job, or official-art preference, and consults neither the connectivity probe nor any image-generation service

#### Scenario: Official rows carry the defined row shape and field semantics
- **WHEN** official_entries is computed
- **THEN** each row is exactly {identity, artwork, is_current, is_catalog_default}; artwork is the canonical exact-image descriptor with fingerprinted same-origin URL and geometry in its candidate; the other identity/preference fields keep their current meaning

#### Scenario: Official rows never merge into the cards list

- **WHEN** official rows are presented
- **THEN** they are selectable/previewable presentation data only, never derived from, appended to, or merged into `GalleryRecord.cards`

#### Scenario: A reference resolving to nothing presents an empty list

- **WHEN** an entity's content reference resolves nothing in the catalog
- **THEN** the panel presents `official_entries: []`

#### Scenario: Both validator sides enforce the official row contract

- **WHEN** an official-row payload crosses the wire
- **THEN** both the Python and JavaScript mirrored validators enforce the exact row shape, bounds, and URL vocabulary, rejecting payloads accepted on only one side

#### Scenario: The official list and rows are bounded
- **WHEN** official_entries is assembled
- **THEN** it holds at most 32 rows; identity stays at most 192 code points; descriptor candidate URLs stay within the shared 256-code-point bound and the entire canonical envelope bound remains enforced

#### Scenario: The URL budget is pinned because official URLs embed filenames

- **WHEN** the per-row URL budget is justified
- **THEN** it is pinned to the portrait media-URL constant because a fingerprinted official URL embeds an operator-chosen filename

#### Scenario: An over-budget catalog image is omitted, not fatal

- **WHEN** a catalog image's identity or URL exceeds the budget
- **THEN** it is omitted from the list with one bounded diagnostic instead of failing the whole panel, exactly as the portrait payload's official branch falls through over budget

#### Scenario: Personal preference availability is explicit
- **WHEN** a species gallery row has no live individual preference target
- **THEN** capabilities.supports_personal_official_preferences is false, official rows remain previewable, and both validators enforce the new boolean; eligible character rows retain true

#### Scenario: Gallery consumers cut over together
- **WHEN** gallery schema 4 is shipped
- **THEN** the server presenter, both validators, `PANEL_ALLOWLIST` and the client surface switch together; the version-3 rail, filters and their validators are removed without a dual-shape adapter, and old url/face_rect/stage row fields stay rejected


### Requirement: Subject selection is session presentation state retired with the options layer

Canonical requirement ID: `webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer`.

The selected category and the selected subject of each category SHALL be stored
per live WebSocket presentation sequence for the owning character, defaulting to
`mine` and the live character. The store SHALL be retired at disconnect, unpuppet,
and account character switch, exactly like the session options state.

#### Scenario: Selecting a companion re-renders the companion's gallery

- **WHEN** a client dispatches `gallery.category.select` for `party` and then `gallery.subject.select` naming a listed companion subject
- **THEN** both results succeed, the last update contains freshly rendered gallery, art, and roster with gallery's `category` `party` and `selected` naming that subject, and no `GalleryRecord` was touched

#### Scenario: A retired selection falls back to the puppet

- **WHEN** the selected companion is destroyed and the panel is re-rendered
- **THEN** `selected` falls back to the category default (the first listed companion, or null for an empty party) and the panel is available

#### Scenario: Unpuppet clears the selection

- **WHEN** the session unpuppets and later puppets again
- **THEN** the new sequence opens on `mine` with the new puppet selected and no prior selection survives

#### Scenario: A stale selection silently re-selects the puppet

- **WHEN** the stored selection names a subject no longer listed in its category, or a category that is disabled
- **THEN** the panel re-selects the category default, or `mine`, at render time without an error

#### Scenario: The write API validates rail-grammar keys

- **WHEN** the store's write API is called with a grammar-valid subject key
- **THEN** it reports `unknown_subject` for a key not listed in the selected category

#### Scenario: The ui_action adapter is the store's only caller

- **WHEN** the gallery subject-selection or category-selection `ui_action` adapter writes a selection
- **THEN** those two adapters are the store's only callers, write nothing else, and publishes one affected-panel update containing freshly rendered `gallery`, `art`, and `roster` panels on success or domain rejection under the gallery-management action contract

#### Scenario: Selection state touches no domain data

- **WHEN** any part of this capability runs
- **THEN** it mutates no gallery record, card, or job


### Requirement: Pending jobs and the recorded error render as truthful synthetic rows

One read-only accessor over the art queue surface SHALL supply a subject's
in-flight gallery job image ids and minted timestamps, bounded; each SHALL
render as one `status: "pending"` row (spinner state) ordered with the cards by
timestamp. A `GalleryRecord` carrying `last_error_code` SHALL render as exactly
one `status: "failed"` row.

#### Scenario: An unreachable server surfaces the failed row not a broken panel

- **WHEN** a generation request's job settles failed with the bounded unreachable error code and the panel is re-rendered
- **THEN** the panel is available, lists exactly one failed row with 「暫時無法生成，稍後再試」 and the stable code, and lists no new card

#### Scenario: A pending job renders the spinner row

- **WHEN** a gallery job is queued and not yet settled when the panel renders
- **THEN** exactly one pending row for that image id appears with `status: "pending"`

#### Scenario: The failed row carries the bounded authored message

- **WHEN** a `GalleryRecord` with `last_error_code` renders its failed row
- **THEN** the server-authored message is the bounded 「暫時無法生成，稍後再試」 line carrying the stable code, placed newest by `last_error_at`

#### Scenario: A failed row fabricates no card

- **WHEN** a failed row is rendered
- **THEN** it fabricates no card: `url`, `face_rect` and `stage` are null and its `image_id` is deterministic synthetic state (uuid5 over the subject, the error timestamp, and the code), never a stored card's id

#### Scenario: A settled pending row is dropped

- **WHEN** a pending row's `image_id` also names a listed card (same-pass settle race)
- **THEN** the pending row is dropped

#### Scenario: An unreachable image server never degrades the panel

- **WHEN** the image server is unreachable
- **THEN** the panel is still available: AI-offline generation is a surfaced failed row, never a panel degradation and never a broken card


### Requirement: The gallery payload is exactly version-mirrored across server and client

The panel's schema version SHALL be one server-side constant shared by the
presenter and the registry registration; `web/static/webclient/js/elosern/protocol.js`
SHALL register `gallery: 4` in `PANEL_ALLOWLIST` and mirror every bound in an
exact per-panel validator, and the dual-direction parity tests SHALL reject a
payload accepted on one side and rejected on the other. No existing other
panel's schema or envelope changes. Server and client SHALL ship together.

#### Scenario: A stale client rejects rather than renders
- **WHEN** a gallery payload carries a field outside the mirrored exact schema
- **THEN** both validators reject it and the panel degrades to its recovery path

Real candidate geometry SHALL satisfy the exact bounded finite triple contract; both validator sides SHALL validate canonical descriptor attempts and reject obsolete row geometry keys. Schema version SHALL be 4.

#### Scenario: Both validators enforce identity, ordering, and URL facts
- **WHEN** either validator side checks a gallery payload
- **THEN** it enforces unique canonical UUID image IDs, unique full subject keys, selected membership in an expanded group, the fixed category order, positive confined face rectangles, gallery URLs bound to the selected subject and image with the closed store extensions, and coherent status/flags/chips/provenance

#### Scenario: Synthetic rows are bounded and neutralized
- **WHEN** synthetic rows are validated
- **THEN** pending rows stay bounded to eight and failed rows to one; descriptors retain truthful generation state, no original candidate, false flags and empty chips/provenance

#### Scenario: Every field carries its documented bound
- **WHEN** gallery descriptors are validated
- **THEN** existing row/chip/warning bounds remain; generated original URLs keep their 129 bound, official URLs keep 256, canonical attempts are bounded and the panel carries no byte limit of its own

#### Scenario: Warnings name unique visible cards newest-first
- **WHEN** warning entries are validated
- **THEN** they name unique visible bound cards in newest-first order

#### Scenario: Lone surrogates and unsafe numbers are rejected
- **WHEN** a payload carries lone surrogates or unsafe numbers
- **THEN** both validators reject it

#### Scenario: The oversized gallery fails closed at the JSON limit
- **WHEN** a gallery exceeds the publication logical ceiling, the only byte ceiling the panel has
- **THEN** it fails closed and does not silently truncate cards; a structurally valid gallery larger than one intact frame is accepted and delivered whole

#### Scenario: Invalid stage fails both wire validators
- **WHEN** a canonical original candidate carries invalid stage or a row carries old url/face_rect/stage keys
- **THEN** both Python and active Node validators reject the payload

#### Scenario: Null synthetic stage is accepted at the existing version
- **WHEN** otherwise valid pending/failed rows carry canonical descriptors without real-image geometry
- **THEN** both validators accept schema version 4 without new chips or counts


## ADDED Requirements

### Requirement: The equipment summary and capabilities are server-computed
For a kind declaring binding support, `equipment_summary` SHALL list the four slots with each slot's currently equipped normalized value and registry display name, read from stored equipment state without materializing a handler; otherwise it SHALL be null. `capabilities` SHALL mirror the selected subject kind's declaration and `error_state` SHALL carry the record's last error.

#### Scenario: Monster subjects carry no binding affordances
- **WHEN** the selected subject is a monster visual-species subject
- **THEN** `equipment_summary` is null and `capabilities.supports_bindings` is false

#### Scenario: Capabilities mirror the declaration
- **WHEN** the panel presents `capabilities` for a selected subject
- **THEN** it carries `supports_bindings`, `supports_field_selection`, `supports_free_text`, `supports_face_rect`, `supports_stage`, `supports_card_delete` and `max_cards` from the kind's declaration, plus the server-resolved `supports_personal_official_preferences`

#### Scenario: Accessories summarize as a bounded sorted list
- **WHEN** the equipment summary renders the accessories slot
- **THEN** accessories appear as a sorted list with an equipped-count of at most five

#### Scenario: The equipment summary has the exact slot shape
- **WHEN** `equipment_summary` is validated
- **THEN** it has exactly `weapon_main`, `weapon_off`, `armor`, and `accessories`; a single slot contains exactly `{value, display_name}`, with a null value for no equipment; accessories contain exactly `{value, display_names, equipped_count}`, sorted by Unicode code point with corresponding names and at most five values

#### Scenario: error_state is exactly code and timestamp
- **WHEN** `error_state` is validated
- **THEN** it is exactly `{code, at}` or null; the code matches `[a-z0-9_]{1,64}` and the timestamp is a finite epoch number within the safe JSON numeric range

## REMOVED Requirements

### Requirement: The subject rail names every gallery-bearing subject with companion-first ordering
**Reason**: The 24-row cross-kind rail is replaced by five categories, each bounded by its own source (`webclient-gallery-categories`).
**Migration**: Subjects are listed per category in `groups`; tests move to `webclient-gallery-categories` and the version-4 projection requirements.

### Requirement: Filter counts and the equipment summary are server-computed
**Reason**: The filter tabs and their counts are removed (design D7); the equipment summary rules move to "The equipment summary and capabilities are server-computed".
**Migration**: Retarget equipment and capability tests to the new requirement; delete filter-count tests.
