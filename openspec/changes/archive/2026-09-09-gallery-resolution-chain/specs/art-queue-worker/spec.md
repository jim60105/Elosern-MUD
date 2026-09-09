## MODIFIED Requirements

### Requirement: Media serving maps validated stored identities to same-origin URLs without exposing the store root

`web/art_media.py` SHALL expose a same-origin route that serves only an output identity
referenced by a `done` asset record — never an arbitrary path under the store root — after
applying the same confinement check the worker uses, and SHALL reject `..`, symlinks,
unexpected directories or extensions, absolute paths, and missing or out-of-root identities
with a 404. The accepted extensions are exactly the store extensions of the supported output
formats (`.png`, `.webp`, `.jpg`, `.avif`) — the closed set of ALL store extensions, never the
currently configured format alone, so a store mid-way through a format switch stays servable —
each served with its fixed media type (`image/png`, `image/webp`, `image/jpeg`, `image/avif`
respectively) from a closed extension-to-type map. The read-only presenter SHALL build URLs
only from validated stored identities — a `done` record's stored identity validated against the
subject's directory/key shape and the same closed four-extension set, NOT against the currently
configured output extension — and SHALL never expose `out_path` or the store root.

The route SHALL additionally serve GALLERY identities of the exact shape
`gallery/<kind>/<subject-key>/<image-id>.<ext>`, where `<kind>` is exactly `character` or `monster`
and `<ext>` is one of the same closed four store extensions. A gallery identity SHALL be served only
when the `GalleryRecord` addressed by its own `<kind>`/`<subject-key>` segments holds a card whose
stored identity equals the requested identity exactly — resolved by a direct record lookup, never by
scanning every record — and SHALL otherwise return 404. Every other rejection rule is unchanged:
`..`, symlinks, absolute paths, unexpected directories or extensions, and out-of-root or missing
identities return 404 without exposing the store root. The read-only presenter SHALL build a gallery
URL only from a card's validated stored identity.

The route SHALL additionally serve BUILT-IN FALLBACK identities of the exact shape
`defaults/<fallback-key>.<ext>` from one fixed in-repo defaults directory (never the store root),
with the same closed extension-to-media-type map and the same confinement discipline applied to that
directory; an absent file, an unexpected sub-path, a symlink, or an out-of-directory resolution
SHALL return 404. Serving fallbacks through this one route keeps `/art/...` the single media URL
vocabulary the wire payloads accept.

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

