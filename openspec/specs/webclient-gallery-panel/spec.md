# webclient-gallery-panel Specification

## Purpose
Expose the world art gallery as a read-only presentation panel: a bounded,
companion-first subject rail with session-scoped selection, server-authored card
rows carrying chips, provenance, and validated media URLs, truthful pending and
failed synthetic rows, presenter-computed binding-overlap warnings, and
server-computed filter counts and equipment summary — all mirrored exactly by a
version-pinned dual-direction wire validator so a stale client rejects instead
of rendering, and never reachable by any mutation path.

## Requirements

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

### Requirement: Card rows are server-authored with chips, crown, and validated media
Each card row SHALL contain exactly image_id, status, label, artwork, is_default, chips, requested_fields, binding_present and created_at. Artwork SHALL identify that exact original through the canonical descriptor. Existing newest-first ordering, truthful synthetic status, chips and preference semantics SHALL remain.

#### Scenario: A bound custom-face default card carries its exact chips

- **WHEN** a card bound to `weapon_main`+`armor` with a custom rect is the record default
- **THEN** its chips are 「主手」「防具」「自訂臉框」「目前預設」 and `is_default` is true

#### Scenario: Chips never appear client-side-first

- **WHEN** any card row is rendered by any client
- **THEN** every chip string was present in the committed payload; the client composes none

#### Scenario: Cards minted at different times share the label and keep their instants
- **WHEN** two stored cards with different `created_at` values and one pending job are projected
- **THEN** both card rows read 「肖像」, the pending row reads 「肖像（生成中）」, no label contains a
  timestamp, each row carries its own `created_at`, and no stored record is renamed

#### Scenario: A fitted-default row on a non-square image survives both validator sides
- **WHEN** a card whose `image_size` is 768×1024 carries the fitted default rect `{x:0.25,y:0.06,w:0.5,h:0.375}` and its row chip 「預設臉框」 is validated by the server validator and by its mirrored legacy validator
- **THEN** both accept the row, because neither re-derives the chip from a literal-constant comparison

#### Scenario: A row never carries an image size
- **WHEN** a row is validated
- **THEN** there is no top-level image_size key; admitted decoded dimensions may occur only inside exact canonical candidate geometry

#### Scenario: Real rows carry stage without new chips
- **WHEN** a real card with nonidentity stage is projected
- **THEN** its original candidate geometry carries the exact stage and no new chip/filter is added

#### Scenario: The label is the server-authored zh-TW display line
- **WHEN** a stored-card row or a pending row is projected
- **THEN** its `label` is the server-authored zh-TW display line for the row — stored cards carry no name, so a card row reads 「肖像」 and a pending row 「肖像（生成中）」

#### Scenario: The label never embeds a timestamp
- **WHEN** any row label is authored
- **THEN** it SHALL NOT embed a timestamp, because `created_at` already carries the instant and the client presents it

#### Scenario: A media URL is built only from a fully validated identity
- **WHEN** a card row's media URL is built
- **THEN** it comes only from a card's stored identity validated against the subject's own gallery prefix, the closed extension set, the store-root confinement check, and the file-existence check — exactly the `art-gallery-resolution` presenter discipline

#### Scenario: A card whose file vanished is omitted
- **WHEN** a readable card record names a vanished or invalid output
- **THEN** its card row remains identified with an attributed known-fault descriptor and no original URL; it is never silently omitted or replaced by another card

#### Scenario: Binding chips come from the card's binding mask
- **WHEN** a row's `chips` list is authored
- **THEN** it is the server-authored label list derived from the card's binding mask: `weapon_main` → 「主手」, `weapon_off` → 「副手」, `armor` → 「防具」, `accessories` → 「飾品」

#### Scenario: The face chip names the custom or default frame
- **WHEN** the face fact is authored for a row
- **THEN** it is 「自訂臉框」 when the rect differs from the card's fitted default `default_face_rect(image_size)`, else 「預設臉框」

#### Scenario: The crown chip marks exactly the default card
- **WHEN** a row's chips are authored
- **THEN** 「目前預設」 appears exactly when `is_default`

#### Scenario: Validators never re-derive the face chip
- **WHEN** either validator side checks a row's face chip
- **THEN** it SHALL NOT re-derive which face chip a row must carry from the rect's numeric relation to the literal `DEFAULT_FACE_RECT` constant — the chip is authored server-side against the card's recorded `image_size`, which is not a top-level row field (candidate geometry may carry decoded dimensions), and both validator sides accept either face chip so a fitted-default row on a non-square image stays valid across the wire

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

### Requirement: Binding-overlap warnings are computed only in the presenter

The panel SHALL carry `binding_warnings`: for the selected subject, the bound
cards whose masked slots ALL evaluate equal to the current equipment snapshot on
every slot the card masks (i.e. cards that could satisfy their binding against
the same equipment right now) — the subject's default card included when it is
bound — ordered newest-first, at most five entries.

#### Scenario: Two cards matching the current equipment overlap

- **WHEN** two bound cards' masked slots all equal the puppet's current snapshot
- **THEN** both names appear in `binding_warnings` (newest first) with their per-slot condition lines

#### Scenario: A card whose binding cannot match today is not warned

- **WHEN** a bound card masks `weapon_main` against an item the puppet is not wearing
- **THEN** that card is absent from `binding_warnings`

#### Scenario: Each warning entry has the exact shape

- **WHEN** a `binding_warnings` entry is emitted
- **THEN** it is exactly `{image_id, label, conditions}` where `conditions` is the card's server-authored per-slot condition lines (slot label plus equipped display name; accessories rendered as the sorted list with 「任一」 semantics)

#### Scenario: No warnings is an empty list, never null

- **WHEN** binding is unsupported or nothing overlaps
- **THEN** an empty list is present, not null

#### Scenario: Clients hold no matching rule

- **WHEN** any client renders binding warnings
- **THEN** no matching rule exists in any client; the binding editor renders these facts verbatim

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

### Requirement: The personal selection state is server-authored in the panel payload

The gallery panel SHALL present the selected subject's personal default governance truthfully:
`cards` retains its existing default-card semantics; the personal official selection is visible only
through `official_entries[].is_current`; and no client SHALL compute which of the two personal
defaults governs — the presentation chain (see `official-art-resolution`) decides resolution
server-side and the panel reports the facts verbatim.

#### Scenario: Clients compose nothing

- **WHEN** any client renders official rows alongside card rows
- **THEN** every row, flag, and URL was present in the committed payload, and the client derived none of it locally

### Requirement: The version-4 gallery payload has an exact category-scoped shape
The version-4 available form SHALL contain exactly `schema_version` (4), `available`, `kind`, `categories`, `category`, `groups`, `selected`, `description`, `cards`, `official_entries`, `equipment_summary`, `capabilities`, `binding_warnings` and `error_state`. `categories` SHALL list the five category keys in fixed order with count, enabled and reason; `category` SHALL name an enabled one.

#### Scenario: A payload naming a disabled category is rejected
- **WHEN** a v4 payload's `category` names a category whose `enabled` is false
- **THEN** both validators reject it

#### Scenario: A reordered or partial category list is rejected
- **WHEN** `categories` omits a key, repeats one or changes the order
- **THEN** both validators reject it

#### Scenario: Reason accompanies only disabled categories
- **WHEN** an enabled category carries a reason or a disabled one carries none
- **THEN** both validators reject it

### Requirement: Version-4 groups carry ordered subjects or a collapsed count
Each group SHALL be exactly `{key, label, seen, total, expanded, count, subjects}`. An expanded group SHALL list exactly `count` subjects; a collapsed group SHALL carry an empty list. Each subject SHALL be exactly `{subject_key, kind, display_name, is_current, card_count, artwork}` with unique keys across groups, a coherent kind and a nullable canonical artwork descriptor.

#### Scenario: A collapsed group with subjects is rejected
- **WHEN** a group has `expanded: false` and a non-empty `subjects` list
- **THEN** both validators reject it

#### Scenario: Group counts sum to the category count
- **WHEN** the groups' counts do not sum to the selected category's `count`
- **THEN** both validators reject it

#### Scenario: A collapsed group is accepted
- **WHEN** a group has `expanded: false`, a label, `count: 7` and no subjects, and the counts sum correctly
- **THEN** both validators accept it

#### Scenario: Seen and total are paired and bounded
- **WHEN** a group carries `seen` without `total`, or `seen` greater than `total`
- **THEN** both validators reject it

### Requirement: Selection decides the version-4 card fields
`selected` SHALL be null exactly when no expanded group lists a subject, and otherwise SHALL name a listed subject. While `selected` is null, `cards`, `official_entries` and `binding_warnings` SHALL be empty, and `equipment_summary`, `capabilities`, `error_state` and `description` SHALL be null. Otherwise the card fields SHALL follow the existing row, official, warning and equipment rules.

#### Scenario: An empty category carries no card facts
- **WHEN** a payload has no listed subject, `selected: null` and an empty `cards` list
- **THEN** both validators accept it, and they reject the same payload when `capabilities` is not null

#### Scenario: A selection outside the listed subjects is rejected
- **WHEN** `selected` names a subject that only a collapsed group would contain
- **THEN** both validators reject it

#### Scenario: Capabilities carry the declared card operations
- **WHEN** `capabilities` omits `supports_face_rect`, `supports_stage` or `supports_card_delete`, or carries a non-boolean for one
- **THEN** both validators reject it

### Requirement: A panel past the subject ceiling is unavailable, never truncated
Both validators SHALL reject a version-4 payload listing more than 256 subjects in total. The gallery presenter SHALL NOT drop subjects to fit; a rejected payload SHALL degrade to the common unavailable form through the presenter registry and log the error.

#### Scenario: One subject over the ceiling fails closed
- **WHEN** a payload lists 257 subjects
- **THEN** both validators reject it, and a payload listing 256 otherwise valid subjects is accepted

### Requirement: The version-4 panel has no byte limit of its own
The version-4 validators SHALL bound the panel by its structural limits alone. They SHALL NOT reject a payload for exceeding the size of one intact transport frame; the only byte ceiling applied SHALL be the publication logical ceiling shared with the transport.

#### Scenario: A panel larger than one frame is valid
- **WHEN** a structurally valid version-4 payload serializes to more canonical bytes than one intact frame allows
- **THEN** both validators accept it

### Requirement: The version-4 validators are exact mirrors
Every version-4 rule SHALL be enforced identically by the Python and JavaScript validators, and the dual-direction parity cases SHALL fail when a payload is accepted on one side and rejected on the other.

#### Scenario: Parity cases cover every rule
- **WHEN** the parity test runs its v4 accept and reject cases through both validators
- **THEN** every case has the same verdict on both sides

### Requirement: The version-4 projection carries one category with tile artwork
The version-4 gallery projection SHALL carry every category descriptor and only the selected category's groups. Each listed subject SHALL carry its stored card count and the artwork descriptor of its resolved default image, or null when none resolves. The projection SHALL read only.

#### Scenario: Only the selected category's subjects are listed
- **WHEN** the selection names `party` for an actor with two account characters and one companion
- **THEN** the projection lists exactly the companion and still reports the counts of all five categories

#### Scenario: A tile carries its default artwork without a selection
- **WHEN** a listed companion that is not selected has a default card
- **THEN** its subject row carries that card's artwork descriptor and its card count

#### Scenario: Building twice changes nothing
- **WHEN** the projection is built twice for the same session
- **THEN** both results are identical and no gallery record, card, job or preference changed

### Requirement: The version-4 selection is remembered per category with fallbacks
The session SHALL remember one category and one subject per category for the owning character, kept across possession and retired when the session puppets another owner or ends. A remembered subject no longer listed SHALL fall back to the category default (the live character in `mine`, else the first listed subject, else null); a remembered category that is disabled SHALL fall back to `mine`. A fresh session SHALL open on `mine` with the live character selected.

#### Scenario: A fresh session opens on the live character
- **WHEN** a session with no stored selection builds the projection
- **THEN** `category` is `mine` and `selected` is the live character

#### Scenario: Each category keeps its own subject
- **WHEN** the player selects companion B in `party`, switches to `monster`, selects species `t_a`, then switches back to `party`
- **THEN** `selected` is B

#### Scenario: A vanished subject falls back to the category default
- **WHEN** the remembered `party` subject leaves the party
- **THEN** `selected` is the first listed companion, or null when the party is empty

#### Scenario: Possession keeps the stored selection
- **WHEN** the player possesses a companion after selecting species `t_a` in `monster`
- **THEN** the projection still selects `monster` and `t_a`

#### Scenario: Unknown or disabled targets are refused without a write
- **WHEN** the store is asked to select the disabled `people` category, or a subject not listed in the selected category
- **THEN** it returns the `unknown_category` or `unknown_subject` rejection and the stored selection is unchanged

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
