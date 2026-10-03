## MODIFIED Requirements

### Requirement: The portrait catalog is server-authored, age-checked, and bounded
The art panel `portrait_catalog` SHALL be a bounded object keyed by the opaque IDs of currently
present focusable entities: the combat-session participant identities in combat mode, and the
dialogue hosts and explicit named-portrait-policy characters present in the current room in
exploration mode, in deterministic order. Each catalog value SHALL contain the server-resolved
subject key, asset status, same-origin media URL or placeholder, aspect ratio, alternative text, and
bounded display context (name plus role/target label), and the resolved normalized face rectangle and stage triple. Stage SHALL be an exact finite bounded `{scale, x, y}` mapping for assets and null for placeholders; malformed stored card stage SHALL degrade to identity rather than fail a snapshot. The face rectangle SHALL be a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` whenever the entry carries a media URL, and SHALL be `null` whenever the entry is a placeholder, so a client never offsets a frame it has no image for. The catalog SHALL carry no face-detection result, no crop, and no second image reference. Portrait subject resolution SHALL dispatch by
entity kind: a named character SHALL resolve `portrait:character:<stable-key>` only from an explicit
named `portrait_policy` through the canonical-age check; a generic monster SHALL resolve
`portrait:monster:<archetype>` from its bestiary `MONSTER_TIER_REGISTRY` archetype without any
character age gate; and anything else SHALL be the unavailable placeholder. Eligibility SHALL NOT be
inferred from display name, key shape, or LLM authorship. The canonical-age check SHALL reject a
character when either `age` or `apparent_age` is missing or malformed (non-integer); a rejected
subject SHALL appear as the unavailable placeholder with no subject key, no URL, and no prompt
content, and SHALL NOT be enqueued or reach a worker. The catalog SHALL contain only currently
present focusable identities and SHALL NOT contain persona text, disguised stats, combat resources,
or any subject that
is not currently present.

#### Scenario: Combat catalog mirrors the context_actions participants
- **WHEN** combat presentation resolves participants and the art panel resolves its portrait catalog
- **THEN** the two panels share the same participant identities, and each present participant maps to
  exactly one catalog value keyed by that identity

#### Scenario: A named present character resolves to a verified portrait value
- **WHEN** a present character carries an explicit named portrait policy and passes the canonical-age
  check
- **THEN** its catalog entry carries the resolved subject key and status, a same-origin URL or
  truthful placeholder, and its display context, and no browser-constructed key or URL exists

#### Scenario: A generic monster shares one portrait per bestiary archetype
- **WHEN** a present monster carries a valid bestiary `threat_tier`
- **THEN** its catalog entry resolves `portrait:monster:<threat_tier>` with the archetype-shared asset
  or its placeholder, and its name and role context are keyed by the opaque entity identity

#### Scenario: Missing or malformed age values reject without a prompt
- **WHEN** a present character's `age` or `apparent_age` is missing, non-integer, or otherwise
  malformed
- **THEN** the subject resolves to the unavailable placeholder, nothing is enqueued, and no prompt,
  subject key, or URL is produced

#### Scenario: Non-present entities are excluded
- **WHEN** a room contains entities that are not present (e.g. in another room) or carry no explicit
  named policy and are not dialogue hosts
- **THEN** none of them appears in the portrait catalog

#### Scenario: A resolved catalog entry carries its face rectangle
- **WHEN** a present entity resolves to a gallery image
- **THEN** its catalog entry carries a media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder entry carries a null face rectangle
- **WHEN** a present entity resolves to any truthful placeholder
- **THEN** its catalog entry carries a null URL and a null face rectangle

### Requirement: The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function
Each framed-portrait surface named below SHALL crop its cover-fitted portrait images through one
shared pure mapping from the committed entry's normalized `face_rect` to a CSS `object-position`
percentage pair, exported by `web/webclient-app/components/face-rect.js`, so the server's authored
composition stays centered in a frame of any aspect ratio. Under cover fit the mapping SHALL align
the image's p% point with the frame's p% point, which centers the rectangle's center.
The mapping SHALL return the centered `50% 50%` pair — never a throw and never an off-frame
percentage — for a `null` or `undefined` rectangle and for any rectangle with a non-finite field,
a field outside `[0, 1]`, an `x + w` greater than 1, a `y + h` greater than 1, or a non-positive
`w` or `h`, so one corrupt card cannot blank a portrait surface. A URL-bearing entry whose rectangle
is missing or malformed SHALL still render its image with that centered crop; only a placeholder
entry (a null URL) SHALL render its labelled placeholder with no image element.
Each avatar surface — the combat participant frame, the party strip and the party drawer's
avatar thumbnails, the dialogue host avatar in the narrative feed, the interact target avatars
and the dock's target rows, and the top-bar character switcher — SHALL apply the mapping to that
entry's rectangle and SHALL ignore stage. The drawer's full-figure art slot uses the separate
stage render contract and is excluded from this cover rule. Scene backdrops consume scene media,
not portrait entries, and are outside this requirement.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's object-position centers that rectangle's center (vertically the 31% line), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives null, a non-finite field, an out-of-bounds field, an edge-crossing rectangle or non-positive width/height
- **THEN** it returns centered `50% 50%`, a URL-bearing surface renders that centered cover crop and a null-URL placeholder renders its label without an image

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same entry is rendered by the combat participant frame, party strip, party drawer avatar thumbnails, dialogue host avatar, interact target avatar, dock target row and character switcher
- **THEN** each cover-cropped image applies the shared mapping to its face rectangle, even when the entry carries a nonidentity stage triple

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The ReferenceArtwork component SHALL retain separate cover and stage modes. Its cover mode SHALL
render one URL-bearing image with the shared face_rect crop. The drawer's full-figure art slot
SHALL explicitly use stage mode instead: contain fit, center-bottom positioning and bottom-center
stage scale/translation, without a face_rect crop. A null entry or placeholder entry (null URL)
SHALL render its truthful labelled placeholder with no image; a failed load SHALL degrade to
that mode's labelled placeholder, and a changed URL SHALL re-attempt the new image without
remounting the surface. Stage-mode placeholders SHALL retain the existing inline standing
silhouette and accessible state. The component SHALL remain manifest-listed as
Core/ReferenceArtwork in the frozen required set and covered by the deterministic coverage gate.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** cover mode receives an entry with a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: The drawer full figure consumes stage while avatars retain face crops
- **WHEN** the drawer art slot and avatar thumbnails receive the same URL-bearing portrait with stage `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** the drawer figure uses contain/bottom alignment, scale 0.6 and frame offsets 10%/-20%, while avatar cover crops remain face_rect-driven and unchanged

#### Scenario: A placeholder entry renders no image
- **WHEN** either mode receives a null entry or null URL with a placeholder label
- **THEN** no image element exists and the truthful placeholder state is rendered, retaining the existing standing silhouette in stage mode

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** an image fails to load and the frame later receives a different URL
- **THEN** failure replaces the image with the labelled placeholder and the changed URL renders a new image element with the replacement URL

## ADDED Requirements

### Requirement: Resolved artwork carries stage without changing asset or placeholder truth
Resolved gallery-card portraits SHALL carry validated card stage. A malformed stored stage reaching presentation SHALL degrade to `{scale: 1.0, x: 0.0, y: 0.0}` with one bounded `art_stage_invalid` warning carrying the subject. Classic done assets, fallback portraits and scene assets SHALL carry identity stage; placeholders SHALL carry null. Gallery/art/roster portrait production and stage/dialogue actor consumption SHALL retain this shape, with exact Python and dependency-free Node validators deployed together. Scene rendering SHALL ignore stage, and no new dialogue-host field SHALL be required when the host references the art catalog.

#### Scenario: Gallery portrait carries its card placement
- **WHEN** a subject resolves to a gallery card with stage `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** its resolved portrait, art catalog and actor source carry that triple unchanged

#### Scenario: Malformed stored stage degrades without failed snapshot
- **WHEN** stored malformed stage reaches defensive portrait payload construction
- **THEN** the portrait carries identity stage and one bounded art_stage_invalid warning with subject, while the snapshot remains valid

#### Scenario: Non-card assets and placeholders preserve truthful defaults
- **WHEN** classic done, fallback or scene assets and placeholder branches are resolved
- **THEN** assets carry identity stage, placeholders carry null, and scene visuals remain unchanged

#### Scenario: Exact art validation lands in lockstep
- **WHEN** an otherwise valid asset carries a valid stage triple or a placeholder carries null stage
- **THEN** Python and dependency-free Node validators both accept; missing stage, wrong shape, non-finite/bool or out-of-bounds asset stage and non-null placeholder stage reject on both sides
