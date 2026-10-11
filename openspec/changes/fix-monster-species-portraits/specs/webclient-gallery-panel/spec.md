# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The gallery panel is an exact read-only version-1 presentation panel`
- TO: `### Requirement: The gallery panel is an exact read-only version-2 presentation panel`

## MODIFIED Requirements

### Requirement: The gallery payload is exactly version-mirrored across server and client

The panel's schema version SHALL be one server-side constant shared by the
presenter and the registry registration; `web/static/webclient/js/elosern/protocol.js`
SHALL register `gallery: 2` in `PANEL_ALLOWLIST` and mirror every bound in an
exact per-panel validator, and the dual-direction parity tests SHALL reject a
payload accepted on one side and rejected on the other. No existing other
panel's schema or envelope changes. Server and client SHALL ship together.

#### Scenario: A stale client rejects rather than renders
- **WHEN** a gallery payload carries a field outside the mirrored exact schema
- **THEN** both validators reject it and the panel degrades to its recovery path

Real card stage SHALL satisfy the exact bounded finite triple contract; both
validator sides SHALL reject a missing stage key, null stage on a real card
or non-null stage on a synthetic row. Schema version SHALL be 2.

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
- **THEN** both validators accept at schema version 2 without new chips or counts

### Requirement: The gallery panel is an exact read-only version-2 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 2,
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

#### Scenario: Personal preference availability is explicit
- **WHEN** a species gallery row has no live individual preference target
- **THEN** capabilities.supports_personal_official_preferences is false, official rows remain previewable, and both validators enforce the new boolean; eligible character rows retain true


### Requirement: The subject rail names every gallery-bearing subject with companion-first ordering

`subjects` SHALL be a bounded ordered list (at most 24 rows) of
`{subject_key, kind, display_name, is_puppet}` entries: first the rendered
puppet's own character subject; then live character subjects with a gallery —
active-party companions before all other characters (design §8.3), ordering
facts taken from the party surface; then registered visual-species entries in stable-key order
resolved through the monster kind's typed producer.

#### Scenario: Active party companions precede other characters

- **WHEN** the puppet's account owns a live companion in the puppet's active party and another live character not in the party
- **THEN** the rail lists the party companion before the non-party character

#### Scenario: The bestiary is listed without any scene subject
- **WHEN** the rail is built for a puppet
- **THEN** registered visual-species subjects are eligible in stable-key order within the 24-row budget, retired tiers and scene subjects never appear

#### Scenario: Gallery-less kinds never appear on the rail

- **WHEN** a subject's kind has a capability declaration granting no gallery (the scene kind)
- **THEN** that subject never appears on the rail

#### Scenario: Selection always names a rail entry

- **WHEN** the panel renders
- **THEN** `selected` names one entry of `subjects`

#### Scenario: Truncation preserves the puppet and bestiary
- **WHEN** the puppet, eligible character candidates and visual-species candidates exceed 24 rows
- **THEN** the puppet is retained; reserve at most 23 slots for visual-species rows, taking their stable-key prefix, and fill remaining slots with companions then other characters in numeric identity order; never exceed 24 or reserve an unbounded species count

#### Scenario: Subject keys are unique across the world gallery

- **WHEN** the rail is assembled
- **THEN** full subject keys are unique, and this world gallery is not an account-subject roster

#### Scenario: A malformed candidate is skipped alone

- **WHEN** a subject candidate is malformed
- **THEN** it is skipped independently without affecting the other rows

#### Scenario: Named policies and records gate eligibility

- **WHEN** character subjects are deemed eligible for the rail
- **THEN** named character policies are eligible even without a gallery record, and account characters without a named policy require an existing numeric subject record — except the puppet, whose numeric identity is always eligible


### Requirement: Filter counts and the equipment summary are server-computed

`filters` SHALL be the server-computed counts `{all, defaults, bound, pending,
failed}` over exactly the rows the panel lists. For a kind declaring binding
support, `equipment_summary` SHALL list the four slots with each slot's
currently equipped normalized value and registry display name, read from stored
equipment state without materializing a handler; otherwise it SHALL be null.

#### Scenario: Monster subjects carry no binding affordances

- **WHEN** the selected subject is a monster visual-species subject
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
- **THEN** it mirrors the subject kind's declaration fields the management surface needs (`supports_bindings`, `supports_field_selection`, `supports_free_text`, `max_cards` or null, plus the server-resolved `supports_personal_official_preferences` context flag)

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

