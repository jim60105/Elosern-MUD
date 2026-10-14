# Spec Delta

## MODIFIED Requirements

### Requirement: The gallery panel is an exact read-only version-2 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 3,
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
- **WHEN** gallery schema 3 is shipped
- **THEN** all previews, detail/binding/generation readers and both original editors consume descriptors directly; old url/face_rect/stage row fields are rejected, without a dual-shape adapter

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

### Requirement: The gallery payload is exactly version-mirrored across server and client

The panel's schema version SHALL be one server-side constant shared by the
presenter and the registry registration; `web/static/webclient/js/elosern/protocol.js`
SHALL register `gallery: 3` in `PANEL_ALLOWLIST` and mirror every bound in an
exact per-panel validator, and the dual-direction parity tests SHALL reject a
payload accepted on one side and rejected on the other. No existing other
panel's schema or envelope changes. Server and client SHALL ship together.

#### Scenario: A stale client rejects rather than renders
- **WHEN** a gallery payload carries a field outside the mirrored exact schema
- **THEN** both validators reject it and the panel degrades to its recovery path

Real candidate geometry SHALL satisfy the exact bounded finite triple contract; both validator sides SHALL validate canonical descriptor attempts and reject obsolete row geometry keys. Schema version SHALL be 3.

#### Scenario: Both validators enforce identity, ordering, and URL facts
- **WHEN** either validator side checks a gallery payload
- **THEN** it enforces unique canonical UUID image IDs, unique full subject keys, selected membership, puppet-first ordering, positive confined face rectangles, gallery URLs bound to the selected subject and image with the closed store extensions, coherent status/flags/chips/provenance, and exact nonnegative filter counts

#### Scenario: Synthetic rows are bounded and neutralized
- **WHEN** synthetic rows are validated
- **THEN** pending rows stay bounded to eight and failed rows to one; descriptors retain truthful generation state, no original candidate, false flags and empty chips/provenance

#### Scenario: Every field carries its documented bound
- **WHEN** gallery descriptors are validated
- **THEN** existing row/chip/warning bounds remain; generated original URLs keep their 129 bound, official URLs keep 256, canonical attempts are bounded and the 65,536-byte envelope fails closed

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
- **WHEN** a canonical original candidate carries invalid stage or a row carries old url/face_rect/stage keys
- **THEN** both Python and active Node validators reject the payload

#### Scenario: Null synthetic stage is accepted at the existing version
- **WHEN** otherwise valid pending/failed rows carry canonical descriptors without real-image geometry
- **THEN** both validators accept schema version 3 without new chips or counts

