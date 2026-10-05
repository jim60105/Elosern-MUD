## MODIFIED Requirements

### Requirement: The portrait catalog is server-authored, age-checked, and bounded
The art panel `portrait_catalog` SHALL be a bounded object keyed by the opaque IDs of currently
present focusable entities: the combat-session participant identities in combat mode, and the
dialogue hosts, explicit named-portrait-policy characters, and live party companions of the player
character present in the current room in exploration mode, in deterministic order. Each catalog
value SHALL contain the server-resolved subject key, asset status, same-origin media URL or
placeholder, aspect ratio, alternative text, and bounded display context (name plus role/target
label), and the resolved normalized face rectangle and stage triple, together with the
server-authored portrait origin discriminator establishing the closed vocabulary
`runtime | silhouette | placeholder` on every entry (extended with `official` by the
`official-art-resolution` capability), so image sources are distinguishable without inspecting the
URL. Each stage-eligible value SHALL additionally carry the server-resolved decorative `fallback`
field (key + `/art/defaults/` identity + rectangle, see `art-gallery-fallback`) beside the real
portrait fields — including on placeholder rows and beside a resolved real image, for a
browser-side load-failure re-render — the only image reference the catalog may carry besides the
real one; the fallback field is decorative presentation data and SHALL NOT populate the entry's
real media URL, subject key, face rectangle, stage, or origin. Decorative fallback selection for
an entity WITHOUT a named portrait policy SHALL use validated entity attributes (and the stable
runtime entity identity solely as hash input) exactly per `fallback_key_for`, and SHALL NOT
install a `portrait_policy`, create a gallery record, or enqueue generation. Stage SHALL be an exact finite
bounded `{scale, x, y}` mapping for assets and null for placeholders; malformed stored card stage
SHALL degrade to identity rather than fail a snapshot. The face rectangle SHALL be a mapping of
exactly `x`, `y`, `w`, `h` in `[0, 1]` whenever the entry carries a media URL, and SHALL be `null`
whenever the entry is a placeholder, so a client never offsets a frame it has no image for. The
catalog SHALL carry no face-detection result and no crop. Portrait
subject resolution SHALL dispatch by entity kind: a named character SHALL resolve
`portrait:character:<stable-key>` only from an explicit named `portrait_policy` through the
canonical-age check; a generic monster SHALL resolve `portrait:monster:<archetype>` from its
bestiary `MONSTER_TIER_REGISTRY` archetype without any character age gate; and anything else SHALL
be the unavailable placeholder (whose real fields stay null while the decorative fallback may
carry the attribute-selected silhouette). Eligibility SHALL NOT be inferred from display name, key
shape, or LLM authorship. The canonical-age check SHALL reject a character when either `age` or
`apparent_age` is missing or malformed (non-integer); a rejected character SHALL appear as the
unavailable placeholder with no subject key, no real URL, and no prompt content (its decorative
fallback field is unaffected), and SHALL NOT be enqueued or reach a worker. The catalog SHALL
contain only currently present focusable identities and SHALL NOT contain persona text, disguised
stats, combat resources, or any subject that is not currently present.

#### Scenario: Combat catalog mirrors the context_actions participants
- **WHEN** combat presentation resolves participants and the art panel resolves its portrait catalog
- **THEN** the two panels share the same participant identities, and each present participant maps to exactly one catalog value keyed by that identity

#### Scenario: A named present character resolves to a verified portrait value
- **WHEN** a present character carries an explicit named portrait policy and passes the canonical-age check
- **THEN** its catalog entry carries the resolved subject key and status, a same-origin URL or truthful placeholder, and its display context, and no browser-constructed key or URL exists

#### Scenario: A generic monster shares one portrait per bestiary archetype
- **WHEN** a present monster carries a valid bestiary `threat_tier`
- **THEN** its catalog entry resolves `portrait:monster:<threat_tier>` with the archetype-shared asset or its placeholder, and its name and role context are keyed by the opaque entity identity

#### Scenario: Missing or malformed age values reject without a prompt
- **WHEN** a present character's `age` or `apparent_age` is missing, non-integer, or otherwise malformed
- **THEN** the subject resolves to the unavailable placeholder, nothing is enqueued, and no prompt, subject key, or URL is produced — its decorative `fallback` field may still carry the attribute-selected silhouette while the real fields stay null

#### Scenario: A live party companion is catalogued even without a dialogue policy
- **WHEN** a present companion carries no explicit named portrait policy and is not a dialogue host, and the exploration art panel resolves its portrait catalog
- **THEN** the companion's identity appears in the catalog keyed like any other entry, so a party `portrait_ref` joined by the companion standing figures resolves in the same committed snapshot that carries it

#### Scenario: Non-present entities are excluded
- **WHEN** a room contains entities that are not present (e.g. in another room) or carry no explicit named policy, are not dialogue hosts, and are not live party companions
- **THEN** none of them appears in the portrait catalog

#### Scenario: A resolved catalog entry carries its face rectangle
- **WHEN** a present entity resolves to a gallery image
- **THEN** its catalog entry carries a media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder entry carries a null face rectangle
- **WHEN** a present entity resolves to any truthful placeholder
- **THEN** its catalog entry carries a null URL and a null face rectangle

#### Scenario: A placeholder row can still carry the attribute-selected decorative silhouette
- **WHEN** a present dialogue-host NPC with no named portrait policy and stored sex/apparent-age attributes resolves to the unavailable placeholder
- **THEN** the entry's real URL, subject key, and face rectangle are null, and its decorative `fallback` field carries the attribute-selected identity — not one shared shape for every missing actor — with no policy, gallery record, or job created for the entity

#### Scenario: A resolved real row retains the decorative reference
- **WHEN** a catalog entry resolves a real runtime image
- **THEN** the entry's real fields carry the image with the `runtime` origin and the decorative `fallback` field remains available for a browser-side load-failure re-render

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The ReferenceArtwork component SHALL retain separate cover and stage modes. Its cover mode SHALL
render one URL-bearing image with the shared face_rect crop. The drawer's full-figure art slot
SHALL explicitly use stage mode instead: contain fit, center-bottom positioning and bottom-center
stage scale/translation, without a face_rect crop. A null entry or placeholder entry (null URL)
SHALL render its truthful labelled placeholder with no image; a failed load SHALL degrade to
that mode's labelled placeholder, and a changed URL SHALL re-attempt the new image without
remounting the surface. Stage-mode placeholders SHALL render the attribute-selected built-in
silhouette in place of the former inline standing SVG: the server-carried fallback media identity
(see `art-gallery-fallback`) drawn as a CSS alpha mask of the committed built-in image — mask
semantics explicit, RGB texture never displayed, aspect ratio preserved, the figure aligned to the
stage floor, filled with the existing dark silhouette styling. The actor's name, targeting/focus
behavior, and the accessible missing/pending/failed labels SHALL render outside the decorative
mask, the pending shimmer and reduced-motion behavior SHALL be retained, and if even the bundled
mask resource fails to load the frame SHALL retain the actor name and the truthful text
placeholder with a usable interaction surface. The component SHALL remain manifest-listed as
Core/ReferenceArtwork in the frozen required set and covered by the deterministic coverage gate.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** cover mode receives an entry with a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: The drawer full figure consumes stage while avatars retain face crops
- **WHEN** the drawer art slot and avatar thumbnails receive the same URL-bearing portrait with stage `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** the drawer figure uses contain/bottom alignment, scale 0.6 and frame offsets 10%/-20%, while avatar cover crops remain face_rect-driven and unchanged

#### Scenario: A placeholder entry renders no image
- **WHEN** either mode receives a null entry or null URL with a placeholder label
- **THEN** no image element exists and the truthful placeholder state is rendered

#### Scenario: A stage silhouette is the attribute-selected alpha mask
- **WHEN** a stage-mode entry carries the server-resolved fallback identity for, respectively, an adult male, adult female, boy, girl, elder, and monster subject
- **THEN** the frame renders each committed image's own alpha mask as the dark silhouette at the current stage position — floor-aligned, aspect-preserved, unstretched — with name and state labels outside the mask, and the former inline SVG is no longer rendered

#### Scenario: A silhouette is not a completed portrait
- **WHEN** a stage-mode entry carries silhouette origin with an underlying pending or failed status
- **THEN** the frame shows the mask plus the truthful pending/failed label, runs the pending shimmer only at full motion, and claims no generated success

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** an image fails to load and the frame later receives a different URL
- **THEN** failure replaces the image with the labelled placeholder and the changed URL renders a new image element with the replacement URL

#### Scenario: A failed bundled mask keeps the frame usable
- **WHEN** the fallback mask resource itself fails to load in stage mode
- **THEN** the frame retains the actor name and the truthful text placeholder, and targeting/focus interaction remains usable
