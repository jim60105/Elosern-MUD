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

### Requirement: The gallery panel is an exact read-only version-1 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 1,
available in exploration mode. Its available form SHALL contain exactly
`schema_version`, `available`, `kind` (the literal `gallery`), `subjects`,
`selected`, `filters`, `cards`, `official_entries`, `equipment_summary`, `capabilities`,
`binding_warnings`, and `error_state`. The registered unavailable form SHALL keep the common field set,
reason, and semantics.

#### Scenario: An empty gallery is available, not unavailable

- **WHEN** a puppet whose character has no gallery record and no pending job receives a full snapshot
- **THEN** the `gallery` panel is available with `cards: []`, every filter count zero, and the puppet named as `selected`

#### Scenario: The presenter mutates nothing

- **WHEN** the panel is built twice in a row for the same puppet
- **THEN** every `GalleryRecord`, card, gallery job record, official-art preference, and stored file is byte-for-byte unchanged and both serializations are identical

#### Scenario: Official entries appear without touching cards

- **WHEN** the selected subject's content reference resolves a catalog directory holding three admitted images, one of them the subject's retained personal selection
- **THEN** `official_entries` carries exactly three official rows with the personal selection marked `is_current`, `cards` still lists only the runtime rows, and no filter count changed

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

- **WHEN** `official_entries` is computed
- **THEN** it is the server-computed bounded list of the selected subject's content reference's catalog-admitted official images (see the `official-art-personalization` capability), each row exactly `{identity, url, face_rect, is_current, is_catalog_default}` where `identity` is the stable root-relative official identity, `url` is the fingerprinted same-origin official media URL, `face_rect` is the metadata-or-fitted validated rectangle, `is_current` marks the subject's retained personal selection, and `is_catalog_default` marks the content's default image

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

- **WHEN** `official_entries` is assembled
- **THEN** it holds at most 32 rows, each row's `identity` is at most 192 code points, and each row's `url` stays inside a per-row budget of 256 code points — pinned equal to `world/art/presenter.py::MAX_PORTRAIT_MEDIA_URL`

#### Scenario: The URL budget is pinned because official URLs embed filenames

- **WHEN** the per-row URL budget is justified
- **THEN** it is pinned to the portrait media-URL constant because a fingerprinted official URL embeds an operator-chosen filename

#### Scenario: An over-budget catalog image is omitted, not fatal

- **WHEN** a catalog image's identity or URL exceeds the budget
- **THEN** it is omitted from the list with one bounded diagnostic instead of failing the whole panel, exactly as the portrait payload's official branch falls through over budget

### Requirement: The subject rail names every gallery-bearing subject with companion-first ordering

`subjects` SHALL be a bounded ordered list (at most 24 rows) of
`{subject_key, kind, display_name, is_puppet}` entries: first the rendered
puppet's own character subject; then live character subjects with a gallery —
active-party companions before all other characters (design §8.3), ordering
facts taken from the party surface; then every `MONSTER_TIER_REGISTRY` entry
resolved through the monster kind's typed producer.

#### Scenario: Active party companions precede other characters

- **WHEN** the puppet's account owns a live companion in the puppet's active party and another live character not in the party
- **THEN** the rail lists the party companion before the non-party character

#### Scenario: The bestiary is listed without any scene subject

- **WHEN** the rail is built for any puppet
- **THEN** every monster-tier subject appears and no scene-kind subject appears in any row

#### Scenario: Gallery-less kinds never appear on the rail

- **WHEN** a subject's kind has a capability declaration granting no gallery (the scene kind)
- **THEN** that subject never appears on the rail

#### Scenario: Selection always names a rail entry

- **WHEN** the panel renders
- **THEN** `selected` names one entry of `subjects`

#### Scenario: Truncation preserves the puppet and bestiary

- **WHEN** the bounded rail exceeds its 24-row cap
- **THEN** it reserves space for the puppet and all bestiary entries, truncating only the character candidate list in companion-first, numeric entity primary-key order

#### Scenario: Subject keys are unique across the world gallery

- **WHEN** the rail is assembled
- **THEN** full subject keys are unique, and this world gallery is not an account-subject roster

#### Scenario: A malformed candidate is skipped alone

- **WHEN** a subject candidate is malformed
- **THEN** it is skipped independently without affecting the other rows

#### Scenario: Named policies and records gate eligibility

- **WHEN** character subjects are deemed eligible for the rail
- **THEN** named character policies are eligible even without a gallery record, and account characters without a named policy require an existing numeric subject record — except the puppet, whose numeric identity is always eligible

### Requirement: Subject selection is session presentation state retired with the options layer

Canonical requirement ID: `webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer`.

The selected subject SHALL be stored per live WebSocket-and-puppet presentation
sequence, defaulting to the puppet. The store SHALL be retired at disconnect,
unpuppet, and account character switch, exactly like the session options state.

#### Scenario: Selecting a companion re-renders the companion's gallery

- **WHEN** a client dispatches `gallery.subject.select` naming a listed companion subject
- **THEN** the result succeeds, one update contains freshly rendered gallery, art, and roster with gallery's `selected` naming that subject, and no `GalleryRecord` was touched

#### Scenario: A retired selection falls back to the puppet

- **WHEN** the selected subject's character is destroyed and the panel is re-rendered
- **THEN** `selected` names the puppet again and the panel is available

#### Scenario: Unpuppet clears the selection

- **WHEN** the session unpuppets and later puppets again
- **THEN** the new sequence's selection is the new puppet and no prior selection survives

#### Scenario: A stale selection silently re-selects the puppet

- **WHEN** the stored selection names no current rail entry
- **THEN** the panel re-selects the puppet at render time without an error

#### Scenario: The write API validates rail-grammar keys

- **WHEN** the store's write API is called with a rail-grammar subject key
- **THEN** it reports `unknown_subject` for a key naming no rail entry

#### Scenario: The ui_action adapter is the store's only caller

- **WHEN** the gallery subject-selection `ui_action` adapter writes a selection
- **THEN** it is the store's only caller, writes nothing else, and publishes one affected-panel update containing freshly rendered `gallery`, `art`, and `roster` panels on success or domain rejection under the gallery-management action contract

#### Scenario: Selection state touches no domain data

- **WHEN** any part of this capability runs
- **THEN** it mutates no gallery record, card, or job

### Requirement: Card rows are server-authored with chips, crown, and validated media

Each entry of `cards` SHALL contain exactly `image_id`, `status` (`"card"`,
`"pending"`, or `"failed"`), `label`, `url` or null, `face_rect` or null, `stage` or null, `is_default`,
`chips`, `requested_fields`, `binding_present`, and `created_at`. Card rows come
only from the tolerant card read. `cards` SHALL be ordered newest-first by
`created_at` with append order as the stable tiebreaker.

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
- **WHEN** any card row is checked for the key `image_size`
- **THEN** it fails the exact-key validation — the squareness reference never crosses the wire

#### Scenario: Real rows carry stage without new chips
- **WHEN** a stored card with stage `{scale: 0.6, x: 0.1, y: -0.2}` is projected
- **THEN** its row carries that validated triple and the existing exactly-one-face-chip contract is unchanged, with no stage chip or filter

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
- **WHEN** a card's stored file has vanished
- **THEN** the card is omitted from `cards`, never emitted with a broken URL

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
- **THEN** it SHALL NOT re-derive which face chip a row must carry from the rect's numeric relation to the literal `DEFAULT_FACE_RECT` constant — the chip is authored server-side against the card's recorded `image_size`, which rows never carry (no row admits an `image_size` key), and both validator sides accept either face chip so a fitted-default row on a non-square image stays valid across the wire

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
- **THEN** exactly one pending row for that image id appears and the 生成中 filter count is at least one

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

### Requirement: Filter counts and the equipment summary are server-computed

`filters` SHALL be the server-computed counts `{all, defaults, bound, pending,
failed}` over exactly the rows the panel lists. For a kind declaring binding
support, `equipment_summary` SHALL list the four slots with each slot's
currently equipped normalized value and registry display name, read from stored
equipment state without materializing a handler; otherwise it SHALL be null.

#### Scenario: Monster subjects carry no binding affordances

- **WHEN** the selected subject is a monster-tier subject
- **THEN** `equipment_summary` is null and `capabilities.supports_bindings` is false

#### Scenario: Counts match the listed rows exactly

- **WHEN** the panel lists two bound cards, one default unbound card, one pending row, and one failed row
- **THEN** filters are all 5, defaults 1, bound 2, pending 1, failed 1

#### Scenario: Each filter count names its rows

- **WHEN** the server counts filter rows
- **THEN** 全部 = every row; 預設 counts the default card; 已綁定 counts cards with a binding; 生成中 counts pending rows; 失敗 counts failed rows

#### Scenario: Accessories summarize as a bounded sorted list

- **WHEN** the equipment summary renders the accessories slot
- **THEN** accessories appear as a sorted list with an equipped-count of at most five

#### Scenario: The summary mirrors the kind's declared capabilities

- **WHEN** the panel presents `capabilities`
- **THEN** it mirrors the subject kind's declaration fields the management surface needs (`supports_bindings`, `supports_field_selection`, `supports_free_text`, `max_cards` or null)

#### Scenario: error_state carries the record's last error

- **WHEN** the panel presents `error_state`
- **THEN** it is the record's last error code and timestamp or null

#### Scenario: The equipment summary has the exact slot shape

- **WHEN** `equipment_summary` is validated
- **THEN** it has exactly `weapon_main`, `weapon_off`, `armor`, and `accessories`; a single slot contains exactly `{value, display_name}`, with a null value for no equipment; accessories contain exactly `{value, display_names, equipped_count}`, sorted by Unicode code point with corresponding names and at most five values

#### Scenario: Keys and names are short nonempty strings

- **WHEN** summary keys and display names are validated
- **THEN** each is a nonempty string of at most 64 code points

#### Scenario: error_state is exactly code and timestamp

- **WHEN** `error_state` is validated
- **THEN** it is exactly `{code, at}` or null; the code matches `[a-z0-9_]{1,64}` and the timestamp is a finite epoch number within the safe JSON numeric range

### Requirement: The gallery payload is exactly version-mirrored across server and client

The panel's schema version SHALL be one server-side constant shared by the
presenter and the registry registration; `web/static/webclient/js/elosern/protocol.js`
SHALL register `gallery: 1` in `PANEL_ALLOWLIST` and mirror every bound in an
exact per-panel validator, and the dual-direction parity tests SHALL reject a
payload accepted on one side and rejected on the other. Adding the panel SHALL
be additive: no existing panel's schema or envelope changes.

#### Scenario: A stale client rejects rather than renders

- **WHEN** a gallery payload carries a field outside the mirrored exact schema
- **THEN** both the Python validator and the JavaScript validator reject it and the panel degrades to that renderer's recovery path

Real card stage SHALL satisfy the exact bounded finite triple contract; both validator sides SHALL reject a missing stage key, null stage on a real card or non-null stage on a synthetic row. Schema version SHALL remain 1; server and client SHALL ship together.

#### Scenario: Both validators enforce identity, ordering, and URL facts

- **WHEN** either validator side checks a gallery payload
- **THEN** it enforces unique canonical UUID image IDs, unique full subject keys, selected membership, puppet-first ordering, positive confined face rectangles, gallery URLs bound to the selected subject and image with the closed store extensions, coherent status/flags/chips/provenance, and exact nonnegative filter counts

#### Scenario: Synthetic rows are bounded and neutralized

- **WHEN** synthetic rows are validated
- **THEN** pending rows are bounded to eight and failed rows to one, and synthetic rows carry null URL/rectangle/stage, false flags, and empty chips/provenance

#### Scenario: Every field carries its documented bound

- **WHEN** payload fields are validated
- **THEN** defaults are at most one, labels at most 128 code points, chips at most 16, URLs at most 129, and warning conditions at most four nonempty lines of at most 512 code points

#### Scenario: Warnings name unique visible cards newest-first

- **WHEN** warning entries are validated
- **THEN** they name unique visible bound cards in newest-first order

#### Scenario: Lone surrogates and unsafe numbers are rejected

- **WHEN** a payload carries lone surrogates or unsafe numbers
- **THEN** both validators reject it

#### Scenario: The oversized gallery fails closed at the JSON limit

- **WHEN** a character gallery exceeds the existing 65,536-byte canonical JSON limit
- **THEN** it fails closed and does not silently truncate cards

#### Scenario: Invalid stage fails both wire validators
- **WHEN** a real row has out-of-range stage, a missing stage key or null stage, or a pending/failed row carries a fabricated triple
- **THEN** both Python and dependency-free Node validators reject the payload

#### Scenario: Null synthetic stage is accepted at the existing version
- **WHEN** otherwise valid pending and failed rows carry stage null
- **THEN** both validators accept at schema version 1 without new chips or counts

### Requirement: The personal selection state is server-authored in the panel payload

The gallery panel SHALL present the selected subject's personal default governance truthfully:
`cards` retains its existing default-card semantics; the personal official selection is visible only
through `official_entries[].is_current`; and no client SHALL compute which of the two personal
defaults governs — the presentation chain (see `official-art-resolution`) decides resolution
server-side and the panel reports the facts verbatim.

#### Scenario: Clients compose nothing

- **WHEN** any client renders official rows alongside card rows
- **THEN** every row, flag, and URL was present in the committed payload, and the client derived none of it locally
