# webclient-gallery-panel — delta for square-face-rect-contract

## MODIFIED Requirements

### Requirement: Card rows are server-authored with chips, crown, and validated media

Each entry of `cards` SHALL contain exactly `image_id`, `status` (`"card"`,
`"pending"`, or `"failed"`), `label` (the server-authored zh-TW display line for
the row — stored cards carry no name, so a card row reads 「肖像」 and a pending
row 「肖像（生成中）」; the label SHALL NOT embed a timestamp, because
`created_at` already carries the instant and the client presents it), `url` or null, `face_rect` or null, `is_default`,
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
