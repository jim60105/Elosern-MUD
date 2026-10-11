# Spec Delta

## MODIFIED Requirements

### Requirement: The queue is keyed by subject identity and enqueue is idempotent
`world/art/queue.py::ensure(...)` SHALL be keyed by the full subject key and SHALL be idempotent for an
existing `pending`, `in_progress`, or `done` record. A `missing` record SHALL become `pending`; a
`failed` record SHALL re-enqueue to `pending` on the next ensure or staff retry. Forced staff
regeneration SHALL reset the record to `pending` under the queue lock and SHALL preserve the prior
valid output.

#### Scenario: Two gallery requests for one subject produce two jobs
- **WHEN** a gallery image is requested twice for the same subject
- **THEN** two records exist under two distinct `art:<full-subject-key>:gen:<image-id>` keys, both
  pending, and neither replaced the other

#### Scenario: A gallery job never disturbs the subject record
- **WHEN** a subject has both a classic asset record and an in-flight gallery job
- **THEN** `ensure`, forced requeue, and duplicate consolidation act on the classic record only, and
  the gallery job is untouched

#### Scenario: Gallery jobs are excluded from the staff retry set
- **WHEN** the failed-key listing is taken while gallery job records exist
- **THEN** no gallery job key appears in it and the staff retry path re-enqueues only subject records

#### Scenario: Re-ensuring a pending, in-progress, or done subject is a no-op
- **WHEN** `ensure` is called again for a subject whose record is already `pending`, `in_progress`, or
  `done`
- **THEN** the record is unchanged and no new job is queued

#### Scenario: Missing and failed records become pending
- **WHEN** `ensure` runs for a `missing` record and then for a `failed` record
- **THEN** both become `pending`, and the failed record's attempt count increments

#### Scenario: Forced regeneration resets and preserves the prior output
- **WHEN** a staff requeue resets a `done` subject
- **THEN** the record becomes `pending`, the prior valid output identity is preserved, and a later
  invalid worker result leaves the prior output intact

#### Scenario: Gallery generation bypasses ensure through a separate enqueue
- **WHEN** a gallery image is generated
- **THEN** it SHALL NOT go through `ensure`; `world/art/queue.py` exposes a separate gallery enqueue
  that creates one record per REQUESTED IMAGE under the key `art:<full-subject-key>:gen:<image-id>`
  with a freshly minted image id
- **AND** a gallery request is never collapsed into an existing record

#### Scenario: The gallery key shape cannot collide with the subject key
- **WHEN** gallery job keys `art:<full-subject-key>:gen:<image-id>` coexist with subject keys
  `art:<full-subject-key>`
- **THEN** the gallery key shape never collides with the subject key, so subject consolidation,
  `ensure`, and forced requeue never see a gallery job

#### Scenario: A gallery retry is a new request, not a re-enqueue
- **WHEN** `failed_keys()` or the staff retry path runs
- **THEN** gallery job records are excluded, because a gallery retry is a new request, not a
  re-enqueue

#### Scenario: Both queues share the one lock, ordering, and slot
- **WHEN** subject jobs and gallery jobs are queued together
- **THEN** both queues share the one process-wide queue lock, the one pending ordering, and the one
  worker concurrency slot

#### Scenario: Monster jobs require current visual membership
- **WHEN** ensure, gallery enqueue, retry, claim or settle encounters an unregistered monster visual key, including a retired tier
- **THEN** no current monster card or output is produced or applied; rejection leaves valid scene, character and species jobs independent


### Requirement: Media serving maps validated stored identities to same-origin URLs without exposing the store root

`web/art_media.py` SHALL expose a same-origin route that serves only an output identity referenced
by a `done` asset record — never an arbitrary path under the store root — after applying the same
confinement check the worker uses, and SHALL reject `..`, symlinks, unexpected directories or
extensions, absolute paths, and missing or out-of-root identities with a 404. The read-only
presenter SHALL build URLs only from validated stored identities and SHALL never expose `out_path`
or the store root.

#### Scenario: A built-in fallback identity is served from the defaults directory
- **WHEN** `defaults/<fallback-key>.<ext>` is requested and that file exists in the in-repo defaults directory
- **THEN** the file is served same-origin with a 200 status and the media type of its extension, and no store-root path is consulted

#### Scenario: A missing or escaping fallback identity returns 404
- **WHEN** a `defaults/...` identity names a missing file, a sub-path, a symlink, or a path escaping the defaults directory
- **THEN** the route returns 404

#### Scenario: A card-referenced gallery identity is served same-origin with its type
- **WHEN** a gallery identity referenced by a card of the addressed subject's record is requested
- **THEN** the file is served same-origin with a 200 status and the media type of its extension

#### Scenario: An unreferenced or mis-addressed gallery identity returns 404
- **WHEN** a gallery identity exists on disk but no card of the record addressed by its own path segments references it, or its path segments address a different subject than the card that references it
- **THEN** the route returns 404 and never exposes the store root

#### Scenario: A valid done-record identity is served same-origin with its type
- **WHEN** a `done` record references `scene/<key>.webp` resolving under the store root and it
  is requested
- **THEN** the file is served same-origin with a 200 status and `Content-Type: image/webp`

#### Scenario: An unsupported extension returns 404
- **WHEN** an identity ending in `.jxl`, `.txt`, or no extension is requested even if such a
  file exists under the store root
- **THEN** the route returns 404

#### Scenario: Out-of-root, path-traversal, symlinked, and unreferenced identities return 404
- **WHEN** an identity that resolves outside the store root, contains `..`, is a symlink, is not
  referenced by any `done` record, or names a missing file is requested
- **THEN** the route returns 404 and never exposes the store root

#### Scenario: The presenter URL comes only from a validated stored identity
- **WHEN** the presenter resolves a `done` record
- **THEN** it returns a same-origin URL built from the validated stored identity and never the
  raw `out_path` or an absolute path

#### Scenario: A mixed store keeps presenting during a format switch
- **WHEN** the configured output format is `webp` and a `done` record still references an
  existing `scene/<key>.png` from before the switch
- **THEN** the presenter returns that record as an `asset` with the same-origin
  `/art/scene/<key>.png` URL (not a placeholder), and the route serves the PNG

#### Scenario: A catalog-admitted official identity is served with its fingerprint
- **WHEN** `official/<fingerprint>/<root-relative-path>` is requested for a path the current startup catalog indexes with that fingerprint
- **THEN** the file is served same-origin with a 200 status and the media type of its extension, read directly from the official root, and nothing was copied into the store

#### Scenario: A stale or bogus official fingerprint returns 404 without acquiring
- **WHEN** an official identity names a fingerprint the current catalog does not hold for that path, an unindexed path, or a path escaping the official root
- **THEN** the route returns 404, no download/extraction/re-scan is attempted, and the official root is untouched

#### Scenario: The accepted extension and media-type sets are closed and complete
- **WHEN** the route accepts an identity for serving
- **THEN** the accepted extensions are exactly the store extensions of the supported output formats
  (`.png`, `.webp`, `.jpg`, `.avif`) — the closed set of ALL store extensions, never the currently
  configured format alone, so a store mid-way through a format switch stays servable
- **AND** each is served with its fixed media type (`image/png`, `image/webp`, `image/jpeg`,
  `image/avif` respectively) from a closed extension-to-type map

#### Scenario: The presenter validates the done record's stored identity shape
- **WHEN** the read-only presenter resolves a `done` record's stored identity into a URL
- **THEN** the identity is validated against the subject's directory/key shape and the same closed
  four-extension set, NOT against the currently configured output extension

#### Scenario: Gallery identities are served only on an exact card reference
- **WHEN** a GALLERY identity of the exact shape `gallery/<kind>/<subject-key>/<image-id>.<ext>` is
  requested, where `<kind>` is exactly `character` or `monster` and `<ext>` is one of the same closed
  four store extensions
- **THEN** it is served only when the `GalleryRecord` addressed by its own
  `<kind>`/`<subject-key>` segments holds a card whose stored identity equals the requested identity
  exactly — resolved by a direct record lookup, never by scanning every record — and otherwise
  returns 404
- **AND** every other rejection rule is unchanged: `..`, symlinks, absolute paths, unexpected
  directories or extensions, and out-of-root or missing identities return 404 without exposing the
  store root
- **AND** the read-only presenter builds a gallery URL only from a card's validated stored identity

#### Scenario: Built-in fallbacks keep /art/... the single media URL vocabulary
- **WHEN** a BUILT-IN FALLBACK identity of the exact shape `defaults/<fallback-key>.<ext>` is
  requested
- **THEN** it is served from one fixed in-repo defaults directory (never the store root), with the
  same closed extension-to-media-type map and the same confinement discipline applied to that
  directory; an absent file, an unexpected sub-path, a symlink, or an out-of-directory resolution
  SHALL return 404
- **AND** serving fallbacks through this one route keeps `/art/...` the single media URL vocabulary
  the wire payloads accept

#### Scenario: Official identities are answered from the catalog lookup alone
- **WHEN** an OFFICIAL-COMPONENT identity of the closed shape
  `official/<fingerprint>/<root-relative-image-path>` is requested for an image admitted by the
  startup official-artwork catalog (see the `official-artwork-catalog` capability)
- **THEN** it is served only when the catalog's current snapshot indexes that exact root-relative
  path with that exact fingerprint, answered from the catalog lookup alone — never by accepting a
  caller-supplied filesystem path — under the same closed extension-to-media-type map and the same
  no-symlink, in-root confinement discipline applied to `ART_OFFICIAL_ROOT`
- **AND** a missing file, an unindexed path, a stale fingerprint (for example after a maintenance
  restart replaced the bytes), a sub-path escape, a symlink, or an out-of-root resolution SHALL
  return 404
- **AND** the game SHALL NOT retain historical artwork to serve old URLs, and a 404 SHALL NOT trigger
  any download, extraction, or re-scan
- **AND** personal gallery URLs and built-in `defaults/` URLs retain their existing ownership and
  confinement rules unchanged

#### Scenario: Referenced tier artwork remains unservable
- **WHEN** a retired tier monster classic or gallery identity is requested, even with a done record or exact old card reference
- **THEN** the route returns 404; registered species runtime identities, admitted official artwork and monster_anon remain servable through their existing confined routes

