# Delta spec: webclient-gallery-panel (webclient-gallery-panel)

## ADDED Requirements

### Requirement: The gallery panel is an exact read-only version-1 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 1,
available in exploration mode. Its available form SHALL contain exactly
`schema_version`, `available`, `kind` (the literal `gallery`), `subjects`,
`selected`, `filters`, `cards`, `equipment_summary`, `capabilities`,
`binding_warnings`, and `error_state`. The registered unavailable form SHALL keep the common field set,
reason, and semantics. Building the panel SHALL NOT create, mutate, or delete a
`GalleryRecord`, any card, or any gallery job, and SHALL NOT consult the
connectivity probe or any image-generation service.

#### Scenario: An empty gallery is available, not unavailable

- **WHEN** a puppet whose character has no gallery record and no pending job receives a full snapshot
- **THEN** the `gallery` panel is available with `cards: []`, every filter count zero, and the puppet named as `selected`

#### Scenario: The presenter mutates nothing

- **WHEN** the panel is built twice in a row for the same puppet
- **THEN** every `GalleryRecord`, card, gallery job record, and stored file is byte-for-byte unchanged and both serializations are identical

### Requirement: The subject rail names every gallery-bearing subject with companion-first ordering

`subjects` SHALL be a bounded ordered list (at most 24 rows) of
`{subject_key, kind, display_name, is_puppet}` entries: first the rendered
puppet's own character subject; then live character subjects with a gallery —
active-party companions before all other characters (design §8.3), ordering
facts taken from the party surface; then every `MONSTER_TIER_REGISTRY` entry
resolved through the monster kind's typed producer. Subjects of a kind whose
capability declaration grants no gallery (the scene kind) SHALL never appear.
`selected` SHALL name one entry of `subjects`.

#### Scenario: Active party companions precede other characters

- **WHEN** the puppet's account owns a live companion in the puppet's active party and another live character not in the party
- **THEN** the rail lists the party companion before the non-party character

#### Scenario: The bestiary is listed without any scene subject

- **WHEN** the rail is built for any puppet
- **THEN** every monster-tier subject appears and no scene-kind subject appears in any row

### Requirement: Subject selection is session presentation state retired with the options layer

The selected subject SHALL be stored per live WebSocket-and-puppet presentation
sequence, defaulting to the puppet. A selection naming no current rail entry
SHALL re-select the puppet at render time without an error. The store SHALL be
retired at disconnect, unpuppet, and account character switch, exactly like the
session options state. The store SHALL expose a write API taking a
rail-grammar subject key and reporting `unknown_subject` for a key naming no
rail entry; the ui_action adapter registered by the companion
`webclient-gallery-actions` change is its only caller, writes nothing else, and
publishes a `gallery`-affected panel update. Nothing in this capability mutates
a gallery record, card, or job.

#### Scenario: Selecting a companion re-renders the companion's gallery

- **WHEN** a client dispatches `gallery.subject.select` naming a listed companion subject
- **THEN** the result succeeds, one `gallery` panel update is published whose `selected` names that subject, and no `GalleryRecord` was touched

#### Scenario: A retired selection falls back to the puppet

- **WHEN** the selected subject's character is destroyed and the panel is re-rendered
- **THEN** `selected` names the puppet again and the panel is available

#### Scenario: Unpuppet clears the selection

- **WHEN** the session unpuppets and later puppets again
- **THEN** the new sequence's selection is the new puppet and no prior selection survives

### Requirement: Card rows are server-authored with chips, crown, and validated media

Each entry of `cards` SHALL contain exactly `image_id`, `status` (`"card"`,
`"pending"`, or `"failed"`), `label` (the server-authored zh-TW display line for
the row — stored cards carry no name, so the label is derived from the row's
timestamp/sequence by the presenter; a pending row's label carries the
「生成中」 suffix), `url` or null, `face_rect` or null, `is_default`,
`chips`, `requested_fields`, `binding_present`, and `created_at`. Card rows come
only from the tolerant card read; a media URL SHALL be built only from a card's
stored identity validated against the subject's own gallery prefix, the closed
extension set, and the store-root confinement check — exactly the
`art-gallery-resolution` presenter discipline. `chips` SHALL be the
server-authored label list derived from the card's binding mask (`weapon_main`
→ 「主手」, `weapon_off` → 「副手」, `armor` → 「防具」, `accessories` → 「飾品」),
the face fact 「自訂臉框」 when the rect differs from `DEFAULT_FACE_RECT` else
「預設臉框」, and 「目前預設」 exactly when `is_default`. `cards` SHALL be ordered
newest-first by `created_at` with append order as the stable tiebreaker.

#### Scenario: A bound custom-face default card carries its exact chips

- **WHEN** a card bound to `weapon_main`+`armor` with a custom rect is the record default
- **THEN** its chips are 「主手」「防具」「自訂臉框」「目前預設」 and `is_default` is true

#### Scenario: Chips never appear client-side-first

- **WHEN** any card row is rendered by any client
- **THEN** every chip string was present in the committed payload; the client composes none

### Requirement: Pending jobs and the recorded error render as truthful synthetic rows

One read-only accessor over the art queue surface SHALL supply a subject's
in-flight gallery job image ids and minted timestamps, bounded; each SHALL
render as one `status: "pending"` row (spinner state) ordered with the cards by
timestamp. A `GalleryRecord` carrying `last_error_code` SHALL render as exactly
one `status: "failed"` row whose server-authored message is the bounded
「暫時無法生成，稍後再試」 line carrying the stable code, placed newest by
`last_error_at`. A failed row SHALL NOT fabricate a card: `url` and `face_rect`
are null and no `image_id` of a stored card is reused. With the image server
unreachable the panel SHALL still be available: AI-offline generation is a
surfaced failed row, never a panel degradation and never a broken card.

#### Scenario: An unreachable server surfaces the failed row not a broken panel

- **WHEN** a generation request's job settles failed with the bounded unreachable error code and the panel is re-rendered
- **THEN** the panel is available, lists exactly one failed row with 「暫時無法生成，稍後再試」 and the stable code, and lists no new card

#### Scenario: A pending job renders the spinner row

- **WHEN** a gallery job is queued and not yet settled when the panel renders
- **THEN** exactly one pending row for that image id appears and the 生成中 filter count is at least one

### Requirement: Binding-overlap warnings are computed only in the presenter

The panel SHALL carry `binding_warnings`: for the selected subject, the bound
cards whose masked slots ALL evaluate equal to the current equipment snapshot on
every slot the card masks (i.e. cards that could satisfy their binding against
the same equipment right now), excluding the subject's default card, ordered
newest-first, at most five entries, each exactly `{image_id, label,
conditions}` where `conditions` is the card's server-authored per-slot
condition lines (slot label plus equipped display name; accessories rendered as
the sorted list with 「任一」 semantics). An empty list SHALL be present, not
null, whenever binding is unsupported or nothing overlaps. No matching rule
SHALL exist in any client; the binding editor renders these facts verbatim.

#### Scenario: Two cards matching the current equipment overlap

- **WHEN** two bound cards' masked slots all equal the puppet's current snapshot
- **THEN** both names appear in `binding_warnings` (newest first) with their per-slot condition lines

#### Scenario: A card whose binding cannot match today is not warned

- **WHEN** a bound card masks `weapon_main` against an item the puppet is not wearing
- **THEN** that card is absent from `binding_warnings`

### Requirement: Filter counts and the equipment summary are server-computed

`filters` SHALL be the server-computed counts `{all, defaults, bound, pending,
failed}` over exactly the rows the panel lists (全部 = every row; 預設 counts
the default card; 已綁定 counts cards with a binding; 生成中 counts pending
rows; 失敗 counts failed rows). For a kind declaring binding support,
`equipment_summary` SHALL list the four slots with each slot's currently
equipped normalized value and registry display name (accessories as a sorted
list with an equipped-count of at most five), read from stored equipment state
without materializing a handler; otherwise it SHALL be null. `capabilities`
SHALL mirror the subject kind's declaration fields the management surface needs
(`supports_bindings`, `supports_field_selection`, `supports_free_text`,
`max_cards` or null). `error_state` SHALL be the record's last error code and
timestamp or null.

#### Scenario: Monster subjects carry no binding affordances

- **WHEN** the selected subject is a monster-tier subject
- **THEN** `equipment_summary` is null and `capabilities.supports_bindings` is false

#### Scenario: Counts match the listed rows exactly

- **WHEN** the panel lists two bound cards, one default unbound card, one pending row, and one failed row
- **THEN** filters are all 5, defaults 1, bound 2, pending 1, failed 1

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
