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
the face fact 「自訂臉框」 when the rect differs from `DEFAULT_FACE_RECT` else
「預設臉框」, and 「目前預設」 exactly when `is_default`. `cards` SHALL be ordered
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
