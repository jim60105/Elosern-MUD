## MODIFIED Requirements

### Requirement: Card rows are server-authored with chips, crown, and validated media

Each entry of `cards` SHALL contain exactly `image_id`, `status` (`"card"`,
`"pending"`, or `"failed"`), `label` (the server-authored zh-TW display line for
the row — stored cards carry no name, so a card row reads 「肖像」 and a pending
row 「肖像（生成中）」; the label SHALL NOT embed a timestamp, because
`created_at` already carries the instant and the client presents it), `url` or null, `face_rect` or null, `stage` or null, `is_default`,
`chips`, `requested_fields`, `binding_present`, and `created_at`. Card rows come
only from the tolerant card read; a media URL SHALL be built only from a card's
stored identity validated against the subject's own gallery prefix, the closed
extension set, the store-root confinement check, and the file-existence check —
exactly the `art-gallery-resolution` presenter discipline: a card whose stored
file has vanished SHALL be omitted from `cards`, never emitted with a broken
URL. `chips` SHALL be the
server-authored label list derived from the card's binding mask (`weapon_main`
→ 「主手」, `weapon_off` → 「副手」, `armor` → 「防具」, `accessories` → 「飾品」),
the face fact 「自訂臉框」 when the rect differs from the card's fitted default
`default_face_rect(image_size)` else 「預設臉框」, and 「目前預設」 exactly when
`is_default`. The row validators SHALL NOT re-derive which face chip a row must
carry from the rect's numeric relation to the literal `DEFAULT_FACE_RECT`
constant — the chip is authored server-side against the card's recorded
`image_size`, which rows never carry (no row admits an `image_size` key), and
both validator sides accept either face chip so a fitted-default row on a
non-square image stays valid across the wire. `cards` SHALL be ordered
newest-first by `created_at` with append order as the stable tiebreaker.

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


### Requirement: Pending jobs and the recorded error render as truthful synthetic rows

One read-only accessor over the art queue surface SHALL supply a subject's
in-flight gallery job image ids and minted timestamps, bounded; each SHALL
render as one `status: "pending"` row (spinner state) ordered with the cards by
timestamp. A `GalleryRecord` carrying `last_error_code` SHALL render as exactly
one `status: "failed"` row whose server-authored message is the bounded
「暫時無法生成，稍後再試」 line carrying the stable code, placed newest by
`last_error_at`. A failed row SHALL NOT fabricate a card: `url`, `face_rect` and `stage`
are null and its `image_id` SHALL be deterministic synthetic state (uuid5 over
the subject, the error timestamp, and the code), never a stored card's id. A
pending row whose `image_id` also names a listed card (same-pass settle race)
SHALL be dropped. With the image server
unreachable the panel SHALL still be available: AI-offline generation is a
surfaced failed row, never a panel degradation and never a broken card.

#### Scenario: An unreachable server surfaces the failed row not a broken panel

- **WHEN** a generation request's job settles failed with the bounded unreachable error code and the panel is re-rendered
- **THEN** the panel is available, lists exactly one failed row with 「暫時無法生成，稍後再試」 and the stable code, and lists no new card

#### Scenario: A pending job renders the spinner row

- **WHEN** a gallery job is queued and not yet settled when the panel renders
- **THEN** exactly one pending row for that image id appears and the 生成中 filter count is at least one

### Requirement: The gallery payload is exactly version-mirrored across server and client

The panel's schema version SHALL be one server-side constant shared by the
presenter and the registry registration; `web/static/webclient/js/elosern/protocol.js`
SHALL register `gallery: 1` in `PANEL_ALLOWLIST` and mirror every bound in an
exact per-panel validator, and the dual-direction parity tests SHALL reject a
payload accepted on one side and rejected on the other. Adding the panel SHALL
be additive: no existing panel's schema or envelope changes.

Both validators SHALL enforce unique canonical UUID image IDs, unique full
subject keys, selected membership, puppet-first ordering, positive confined
face rectangles, gallery URLs bound to the selected subject and image with the
closed store extensions, coherent status/flags/chips/provenance, and exact
nonnegative filter counts. Pending rows SHALL be bounded to eight and failed
rows to one; synthetic rows SHALL have null URL/rectangle/stage, false flags, and empty
chips/provenance. Defaults SHALL be at most one. Labels SHALL be at most 128
code points, chips at most 16, URLs at most 129, and warning conditions at most
four nonempty lines of at most 512 code points. Warnings SHALL name unique
visible bound cards in newest-first order. Lone surrogates and unsafe numbers
SHALL be rejected. The existing 65,536-byte canonical JSON limit SHALL apply;
an oversized character gallery SHALL fail closed, not silently truncate cards.

#### Scenario: A stale client rejects rather than renders

- **WHEN** a gallery payload carries a field outside the mirrored exact schema
- **THEN** both the Python validator and the JavaScript validator reject it and the panel degrades to that renderer's recovery path

Real card stage SHALL satisfy the exact bounded finite triple contract; both validator sides SHALL reject a missing stage key, null stage on a real card or non-null stage on a synthetic row. Schema version SHALL remain 1; server and client SHALL ship together.

#### Scenario: Invalid stage fails both wire validators
- **WHEN** a real row has out-of-range stage, a missing stage key or null stage, or a pending/failed row carries a fabricated triple
- **THEN** both Python and dependency-free Node validators reject the payload

#### Scenario: Null synthetic stage is accepted at the existing version
- **WHEN** otherwise valid pending and failed rows carry stage null
- **THEN** both validators accept at schema version 1 without new chips or counts


