## MODIFIED Requirements

### Requirement: The gallery panel is an exact read-only version-1 presentation panel

The presentation registry SHALL register a `gallery` panel at schema version 1,
available in exploration mode. Its available form SHALL contain exactly
`schema_version`, `available`, `kind` (the literal `gallery`), `subjects`,
`selected`, `filters`, `cards`, `official_entries`, `equipment_summary`, `capabilities`,
`binding_warnings`, and `error_state`. The registered unavailable form SHALL keep the common field set,
reason, and semantics. Building the panel SHALL NOT create, mutate, or delete a
`GalleryRecord`, any card, any gallery job, or any official-art preference, and SHALL NOT consult the
connectivity probe or any image-generation service. `official_entries` SHALL be the server-computed,
bounded list of the selected subject's content reference's catalog-admitted official images (see the
`official-art-personalization` capability), each row exactly `{identity, url, face_rect, is_current,
is_catalog_default}` where `identity` is the stable root-relative official identity, `url` is the
fingerprinted same-origin official media URL, `face_rect` is the metadata-or-fitted validated
rectangle, `is_current` marks the subject's retained personal selection, and `is_catalog_default`
marks the content's default image; official rows are selectable/previewable presentation data only
and SHALL NOT be derived from, appended to, or merged into `GalleryRecord.cards`. An entity whose
content reference resolves nothing in the catalog SHALL present `official_entries: []`. Both the
Python and JavaScript mirrored validators SHALL enforce the exact row shape, bounds, and URL
vocabulary, rejecting payloads accepted on only one side.

`official_entries` SHALL hold at most 32 rows. Each row's `identity` SHALL be at most 192 code
points and its `url` SHALL stay inside a per-row budget of 256 code points — pinned equal to
`world/art/presenter.py::MAX_PORTRAIT_MEDIA_URL` — because a fingerprinted official URL embeds an
operator-chosen filename; a catalog image whose identity or URL exceeds that budget SHALL be
omitted from the list with one bounded diagnostic instead of failing the whole panel, exactly as
the portrait payload's official branch falls through over budget.

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

## ADDED Requirements

### Requirement: The personal selection state is server-authored in the panel payload

The gallery panel SHALL present the selected subject's personal default governance truthfully:
`cards` retains its existing default-card semantics; the personal official selection is visible only
through `official_entries[].is_current`; and no client SHALL compute which of the two personal
defaults governs — the presentation chain (see `official-art-resolution`) decides resolution
server-side and the panel reports the facts verbatim.

#### Scenario: Clients compose nothing

- **WHEN** any client renders official rows alongside card rows
- **THEN** every row, flag, and URL was present in the committed payload, and the client derived none of it locally
