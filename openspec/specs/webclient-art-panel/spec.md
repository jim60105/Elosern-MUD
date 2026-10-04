## Purpose

The browser's graphical art surface: an exact read-only `art` panel available in
exploration and combat modes, a validated scene payload with truthful
placeholders, a server-authored age-checked portrait catalog, client-local
contextual portrait focus, targeted worker-completion pushes, deterministic
offline degradation, and keyboard-first desktop-bounded browser acceptance.

## Requirements

### Requirement: The art panel is an exact read-only panel available in exploration and combat modes
The production presentation registry SHALL register `art` schema version 2. Its available payload
SHALL contain exactly `schema_version`, `available`, `kind`, `scene`, and `portrait_catalog`;
`available` SHALL be true and `kind` SHALL be `scene`. The panel SHALL be available in `exploration`
and `combat` modes and SHALL use the registered common unavailable form in `creation` mode. The
presenter SHALL strictly read the authenticated puppet's current location and (in combat) its active
combat session, SHALL emit no live object reference, no filesystem path, no store root, and no
rejected prompt content, and SHALL NOT mutate traits, resources, buffs, sexual state, combat
session, map knowledge, quests, location, art records, or world time.

#### Scenario: Exploration mode renders the current scene
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot for a room whose
  validated scene archetype resolves in the registry
- **THEN** the `art` panel is available with the scene payload for that archetype and a bounded
  portrait catalog of currently present focusable entities, and a before/after comparison of
  canonical game state is unchanged

#### Scenario: Combat mode keeps the scene and adds session participants
- **WHEN** the same browser is in an active persistent combat session
- **THEN** the `art` panel remains available with the current scene and the portrait catalog is
  keyed by the same participant identities the `context_actions` panel presents

#### Scenario: Creation mode shows the common unavailable form
- **WHEN** the active puppet is a creation-pending shell
- **THEN** the `art` panel uses its schema-valid unavailable form and contains no scene or portrait
  value

#### Scenario: Presenter failure remains isolated
- **WHEN** art presentation raises while status, map, services, and narrative remain healthy
- **THEN** only `art` becomes correlated unavailable, the other panels still render, and normal text
  output remains usable

### Requirement: The scene payload resolves only validated archetypes with truthful placeholders
The art panel scene SHALL resolve through `world.art.presenter.resolve_scene` from the current room's
validated `scene_archetype` and SHALL contain the subject key, asset status, same-origin media URL,
aspect ratio, and alternative text for a `done` record, or a truthful placeholder kind and
explanatory label otherwise. The scene SHALL render as the client's full-bleed stage backdrop with
cover-style cropping, and SHALL display its label and alternative text as text outside the bitmap.
When the current scene is pending and a prior scene is already rendered, the client SHALL retain that
prior image visibly dimmed and labelled `目前場景圖片生成中`; without a prior image, and for failed or
invalid assets, it SHALL render the current mode's gradient stage together with the scene placeholder
label. The panel SHALL NOT silently present old art as current, SHALL NOT expose `out_path` or the
store root, and SHALL derive its URL only from a validated stored identity.

#### Scenario: Done scene serves the same-origin media URL
- **WHEN** a room's scene archetype has a `done` asset record with an existing validated output
- **THEN** the scene payload carries the asset status, the same-origin `/art/...` URL, 16:9 aspect,
  and meaningful alternative text, and never an absolute filesystem path

#### Scenario: Pending scene retains a labelled prior image
- **WHEN** the current scene is pending and a prior scene image is already rendered
- **THEN** the backdrop keeps that prior image dimmed with the explicit `目前場景圖片生成中` label and the
  pending status rather than presenting it as current art

#### Scenario: Failed, missing, or invalid scene uses the gradient stage and placeholder label
- **WHEN** the scene asset is failed, missing, scheduler-disabled, or its output file is absent
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as
  text and no URL, and no stale image is substituted

### Requirement: The portrait catalog is server-authored, age-checked, and bounded
The art panel `portrait_catalog` SHALL be a bounded object keyed by the opaque IDs of currently
present focusable entities: the combat-session participant identities in combat mode, and the
dialogue hosts, explicit named-portrait-policy characters, and live party companions of the player
character present in the current room in exploration mode, in deterministic order. Each catalog
value SHALL contain the server-resolved subject key, asset status, same-origin media URL or
placeholder, aspect ratio, alternative text, and bounded display context (name plus role/target
label), and the resolved normalized face rectangle and stage triple. Stage SHALL be an exact finite
bounded `{scale, x, y}` mapping for assets and null for placeholders; malformed stored card stage
SHALL degrade to identity rather than fail a snapshot. The face rectangle SHALL be a mapping of
exactly `x`, `y`, `w`, `h` in `[0, 1]` whenever the entry carries a media URL, and SHALL be `null`
whenever the entry is a placeholder, so a client never offsets a frame it has no image for. The
catalog SHALL carry no face-detection result, no crop, and no second image reference. Portrait
subject resolution SHALL dispatch by entity kind: a named character SHALL resolve
`portrait:character:<stable-key>` only from an explicit named `portrait_policy` through the
canonical-age check; a generic monster SHALL resolve `portrait:monster:<archetype>` from its
bestiary `MONSTER_TIER_REGISTRY` archetype without any character age gate; and anything else SHALL
be the unavailable placeholder. Eligibility SHALL NOT be inferred from display name, key shape, or
LLM authorship. The canonical-age check SHALL reject a character when either `age` or
`apparent_age` is missing or malformed (non-integer); a rejected subject SHALL appear as the
unavailable placeholder with no subject key, no URL, and no prompt content, and SHALL NOT be
enqueued or reach a worker. The catalog SHALL contain only currently present focusable identities
and SHALL NOT contain persona text, disguised stats, combat resources, or any subject that is not
currently present.

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

#### Scenario: A live party companion is catalogued even without a dialogue policy
- **WHEN** a present companion carries no explicit named portrait policy and is not a dialogue host, and the exploration art panel resolves its portrait catalog
- **THEN** the companion's identity appears in the catalog keyed like any other entry, so a party `portrait_ref` joined by the companion standing figures resolves in the same committed snapshot that carries it

#### Scenario: Non-present entities are excluded
- **WHEN** a room contains entities that are not present (e.g. in another room) or carry no explicit
  named policy, are not dialogue hosts, and are not live party companions
- **THEN** none of them appears in the portrait catalog

#### Scenario: A resolved catalog entry carries its face rectangle
- **WHEN** a present entity resolves to a gallery image
- **THEN** its catalog entry carries a media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder entry carries a null face rectangle
- **WHEN** a present entity resolves to any truthful placeholder
- **THEN** its catalog entry carries a null URL and a null face rectangle

### Requirement: Contextual portrait focus is client-local and verified
The browser SHALL maintain contextual portrait focus entirely client-side: the KeyboardRouter SHALL
emit a focus event and the art renderer SHALL select a supplied catalog value, and there SHALL be no
focus mutation message and no client-constructed subject key, URL, status, or alternative text. A
full snapshot SHALL preserve the current focus only when the focused catalog ID survives the
replacement; otherwise exploration SHALL have no portrait focus and combat SHALL select the first
valid target in deterministic presenter order. No focus SHALL mean no portrait card; a focused
character with a missing portrait SHALL show the portrait placeholder card rather than removal. Menu
descriptors SHALL reference catalog entries by their opaque IDs; this delivery unit supplies the
combat descriptors (its `portrait_ref`), while exploration-menu descriptors that reference the same
catalog arrive with the exploration-menu delivery unit.

#### Scenario: Keyboard focus switches only among catalog entries
- **WHEN** the browser moves focus among present menu descriptors that reference catalog IDs
- **THEN** the art renderer selects the corresponding catalog value without sending any packet and
  without constructing a subject key or URL

#### Scenario: Focus does not survive a vanished catalog entry
- **WHEN** a panel replacement removes the focused catalog ID
- **THEN** exploration shows no portrait card and combat selects the first valid target in
  deterministic presenter order

#### Scenario: No focus means no portrait card
- **WHEN** the browser has no contextual focus
- **THEN** no portrait card is rendered and the scene remains the sole art content

### Requirement: Worker completion pushes a targeted art panel update

Canonical requirement ID: `webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update`.

When an art-worker asset or gallery job settles and emits `asset_completed`,
the `world/art/` settle path SHALL emit a bounded server-side notification
carrying only the completed subject key. For each connected WebClient session
with an active puppet and an already-attached coordinator, the presentation
layer SHALL independently re-render `art`, `gallery`, and `roster` from that
session's current canonical state and current owned presentation selection.
Each available panel SHALL qualify independently: art when its current scene
subject or any portrait-catalog entry references the completed subject key;
gallery when its rendered `selected` equals that key; roster when any rendered
character row's portrait subject key equals that key. Gallery rail membership
alone SHALL NOT qualify a gallery update, and roster qualification SHALL NOT be
limited to the current puppet or characters present in its room.

The presentation layer SHALL publish all qualifying freshly rendered panels
together in one affected-panel `ui_update` at a newer revision per session per
notification, even when art does not qualify or is unavailable. Unavailable
panels SHALL be omitted independently without suppressing another qualifying
panel. When no panel qualifies it SHALL publish nothing and SHALL NOT advance
revision. Existing mode-coherence companion panels SHALL remain permitted.
A non-WebClient session, a session with no active puppet, or a session with no
attached coordinator SHALL receive no completion push.

Late completions SHALL be gated on the freshly rendered current references,
not remembered selections, rooms, sent payloads, or completed image identities.
A completion for an old room, vanished entity, or no-longer-selected gallery
SHALL NOT replace that panel's current content or restore an old selection;
a different panel still referencing the same subject SHALL remain eligible.
Room or present-entity-set changes SHALL continue to replace the art payload
through ordinary presentation updates. Completion rendering SHALL NOT mutate
canonical state, select a card, or set a default. Failed gallery settlement
notifications SHALL refresh truthful pending/error rows under the same rules
without fabricating a portrait or card. Each session SHALL remain isolated so
its rendering/publication failure cannot stop the other sessions or propagate
back into the worker. Delivery SHALL remain on the existing reactor-side
notification path, not the worker thread.

The notification SHALL NOT expose output paths, prompts, or worker internals,
and the `world/art/` package SHALL remain free of any `web/` import. A missed
notification SHALL be repaired by reconnect's current-store full snapshot,
without replaying the missed push.

#### Scenario: A done scene reaches sessions currently showing that scene

- **WHEN** a scene subject completes while connected sessions currently render that scene and neither their selected gallery nor roster portraits references it
- **THEN** each such session receives one newer art panel update with the done URL and no gallery or roster changes, except any required mode-coherence companion panel

#### Scenario: A late completion never replaces the current panel

- **WHEN** a subject completes after the session moved to a different scene or the entity left and no current art, selected-gallery, or roster reference names that subject
- **THEN** no update is published, revision is unchanged, and the completed subject does not replace the currently rendered scene or portrait

#### Scenario: Reconnect resolves current status from the store

- **WHEN** a browser reconnects after an asset or gallery completion notification was missed
- **THEN** the full snapshot renders current art, gallery cards/pending/error state, and roster portraits from the store without replaying the missed push

#### Scenario: A settled gallery job refreshes all three referencing panels together

- **WHEN** a gallery job settles successfully for the session's selected subject and both art's catalog and an owned roster row also reference that subject
- **THEN** one newer update includes art, gallery, and roster, the gallery's pending row is replaced by its canonical stored card, and both portrait panels carry the current resolved value without a full snapshot

#### Scenario: A selected gallery refreshes without an art or roster match

- **WHEN** a settled gallery job's subject equals a session's rendered selected gallery but is absent from its current art scene/catalog and roster portraits
- **THEN** that session receives one newer update containing gallery and not art or roster, with settled card/error facts and recomputed filter counts

#### Scenario: An off-room roster sibling refreshes without an art or gallery match

- **WHEN** a completion subject appears only in an owned non-current roster character's portrait while that character is outside the current puppet's room and another gallery subject is selected
- **THEN** the session receives one newer roster update containing its current owned rows and freshly resolved sibling portrait, with no art or gallery update

#### Scenario: Unavailable art cannot suppress a selected gallery or roster match

- **WHEN** art renders its unavailable form while an available gallery or roster payload references the completed subject
- **THEN** one newer update carries the matching available panels without art

#### Scenario: A changed selection cannot be restored by late completion

- **WHEN** subject A completes after the session selected subject B and A remains on the rail but neither current art nor roster references A
- **THEN** no update is published, gallery remains selected on B, and no pending/card state for A replaces B's displayed gallery

#### Scenario: A subject leaving art can still refresh an owned roster portrait

- **WHEN** a portrait completion arrives after its character left the current scene but an owned roster row still references that subject
- **THEN** roster refreshes from current state while art is omitted if it no longer references the subject

#### Scenario: Failed gallery settlement removes the stale spinner truthfully

- **WHEN** a selected subject's gallery job settles failed and emits its completion notification
- **THEN** a newer gallery update removes that job's pending row, renders the canonical failed row and error state with recomputed counts, creates no card or default, and any qualifying art/roster values follow their existing resolver fallback behavior

#### Scenario: Per-session selections and failures stay isolated

- **WHEN** live webclient sessions have different selected subjects or one session raises while processing a completion
- **THEN** each healthy session is evaluated against only its own current context, nonmatching galleries are not published, and one session's failure neither stops other eligible sessions nor reaches the worker

#### Scenario: Ineligible sessions receive no completion push

- **WHEN** the notification is processed for a non-WebClient transport, a puppet-less session, or a session without an attached coordinator
- **THEN** that session receives no update, and notification handling does not attach a coordinator or change canonical state to make it eligible

### Requirement: Art degradation never blocks gameplay or leaks rejected content
With the worker command fixed to fail and every LLM profile unavailable, movement, dialogue, combat,
quests, and services SHALL proceed through their deterministic paths while every art state degrades
to the approved placeholders. The scheduler disabled, worker unavailable or timed out, missing file
for a done record, invalid output identity, OOB disconnect during completion, and browser image load
failure SHALL each degrade presentation only and log bounded diagnostics. A browser image load
failure SHALL show fallback text/placeholder and SHALL NOT repeatedly fetch without a new URL or
user reload. OOB errors SHALL contain no traceback, local path, unescaped player content, or rejected
prompt content. A missing/pending/failed scene SHALL degrade to a single truthful placeholder label
on the stage backdrop, identified by a stable `data-testid` hook, with the mode gradient as the
rendered stage. Because a snapshot refresh or a Vue re-render can open a transient double-node window
under a loaded runner, the browser acceptance test SHALL gate its placeholder-count assertion on the
shared bounded wait helper (the committed art-panel store state plus a DOM-readiness descriptor,
within one bounded deadline) rather than a single raw `.count()` sample, so the assertion observes the
single visible placeholder node deterministically.

#### Scenario: Offline art never blocks play
- **WHEN** the worker command is fixed to fail and the scheduler is disabled
- **THEN** the player can move, talk, fight, trade, and turn in quests while the stage shows only the
  gradient and its placeholder label, and no gameplay action waits on a job

#### Scenario: Image load failure degrades to fallback
- **WHEN** a rendered scene URL fails to load in the browser
- **THEN** the backdrop shows its fallback gradient and placeholder label and does not repeatedly refetch the same URL

#### Scenario: Rejected content stays out of every error surface
- **WHEN** an art or presentation error occurs
- **THEN** no OOB message or panel payload contains a traceback, filesystem path, rejected prompt, or
  rejected-subject data

#### Scenario: The missing-scene placeholder gate observes a single node
- **WHEN** the art panel is available with a missing scene and a snapshot refresh or Vue re-render
  opens a transient double-node window under a loaded runner
- **THEN** the acceptance test's bounded gate keeps polling the scene backdrop's placeholder
  `data-testid` hook until it observes exactly one visible placeholder node, so the assertion is
  deterministic rather than a single raw `.count()` sample

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape. Portrait catalog entries SHALL render only inside the framed-portrait
surfaces that consume them (the combat participant frame, the party strip and party drawer, the
stage actors that stand the dialogue host and the combat foes in the `actor-right` anchor, the interact
target avatars and dock target rows); the client SHALL render no
standalone portrait catalog strip and no per-portrait full-view control. The
scene label and alternative text SHALL remain visible as text outside the bitmap, alternative text
SHALL be meaningful, and no required information SHALL exist only inside an image. Server-authored
labels SHALL be inserted as text, not trusted HTML, and reduced-motion preference SHALL disable
nonessential transitions. The stage backdrop and the framed portraits SHALL remain usable at both
1440x900 and 1280x720 without the backdrop covering the scene label, the HUD islands, or required
status.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1440x900 and at 1280x720
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation (including the stage actors), and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it

### Requirement: The art panel accepts the normalized in-flight state
The Web art panel schema (Python and JavaScript) SHALL accept every status the presenter can emit —
including the normalized in-flight state — so a generation-in-progress snapshot renders a placeholder
instead of degrading the panel.

#### Scenario: In-flight snapshot renders instead of degrading
- **WHEN** a WebClient receives an art panel payload whose scene or catalog entry carries the
  normalized in-flight status
- **THEN** the panel renders a placeholder and remains available

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
The small-avatar set — the top-bar character switcher's thumbnails and the party drawer's avatar
thumbnails — additionally obeys the dedicated small-avatar zoom-crop requirement below, which
refines this rule for those surfaces by enlarging the crop around the same rectangle while keeping
the identical validation set and the identical centered-crop fallback; every other surface named
here keeps the recenters-only treatment verbatim. Each avatar surface — the combat participant
frame, the party strip and the party drawer's avatar thumbnails, the dialogue host avatar in the
narrative feed, the interact target avatars and the dock's target rows, and the top-bar character
switcher — SHALL apply the mapping to that entry's rectangle and SHALL ignore stage. The drawer's
full-figure art slot uses the separate stage render contract and is excluded from this cover rule.
Scene backdrops consume scene media, not portrait entries, and are outside this requirement.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's object-position centers that rectangle's center (vertically the 31% line), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives null, a non-finite field, an out-of-bounds field, an edge-crossing rectangle or non-positive width/height
- **THEN** it returns centered `50% 50%`, a URL-bearing surface renders that centered cover crop and a null-URL placeholder renders its label without an image

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same entry is rendered by the combat participant frame, party strip, party drawer avatar thumbnails, dialogue host avatar, interact target avatar, dock target row and character switcher
- **THEN** each cover-cropped image applies the shared mapping to its face rectangle, even when the entry carries a nonidentity stage triple

#### Scenario: The surfaces outside the recenters-only list are unchanged by this split
- **WHEN** a gallery card, the gallery detail rail preview, or a ReferenceArtwork cover-mode image renders an entry with a well-formed rectangle
- **THEN** it still renders the recenters-only `object-position` treatment exactly as before — the small-avatar zoom-crop requirement names it in neither its surface set nor its fallbacks

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

### Requirement: Small avatar thumbnails zoom-crop their portrait image to the carried face rectangle through one shared pure function
The small-avatar set — the top-bar character switcher's collapsed-pill thumbnail, the switcher
popover's per-row thumbnails, and the party drawer's per-companion avatar image — SHALL render a
URL-bearing portrait entry by cropping and zooming so the entry's marked face rectangle
substantially fills the frame: through one shared pure mapping exported by
`web/webclient-app/components/face-rect.js`, the image element SHALL be enlarged to `1/w` × `1/h`
of the frame's size (w, h the rectangle's normalized extents) and anchored inside the frame —
which clips the overflow — by the offsets `-x/w` and `-y/h` of the frame's width and height, so
the rectangle's region of the image fills the frame's box. That window is exact for the
pixel-square rectangle the authoring path enforces; for a legacy or hand-authored non-square
rectangle the same enlarge-and-anchor composition fills the frame from the rectangle while
cropping a bounded sliver on the overflowing axis, and it SHALL never blank the image. The
enlargement factor SHALL be clamped to 8× per axis, and the anchor offsets SHALL be derived from the clamped factors so the
rectangle window stays coherent under the clamp. The mapping SHALL validate the rectangle with
exactly the same well-formedness set as the recenters-only mapping — rejecting `null`,
`undefined`, non-finite fields, fields outside `[0, 1]`, `x + w` or `y + h` greater than 1, and
non-positive `w` or `h` — and for any rejected rectangle it SHALL produce no zoom properties,
leaving the image to render the same centered `50% 50%` cover crop it rendered before this
requirement. A placeholder entry (a null URL) SHALL render its existing label or glyph placeholder
with no image element, unchanged. The mapping SHALL ignore `stage`. The zoom is presentation-only:
the server stores rectangles verbatim and SHALL NOT crop, resize, or derive any second image.

#### Scenario: A well-formed rectangle fills a small avatar frame
- **WHEN** the switcher pill thumbnail, a switcher popover row thumbnail, or a party drawer avatar renders a URL-bearing entry whose rectangle is `{x: 0.3, y: 0.1, w: 0.4, h: 0.4}`
- **THEN** the image element is sized to 250% of the frame's width and height and anchored at offsets `-75%`/`-25%` of the frame, so the rectangle's region covers the frame box and the frame clips the rest

#### Scenario: A horizontally off-center rectangle anchors correctly
- **WHEN** a small avatar renders an entry whose rectangle is `{x: 0.6, y: 0.1, w: 0.2, h: 0.2}` (a rect whose center is right of the image center — the case a symmetric fixture cannot mask)
- **THEN** the image element is sized to 500%/500% and anchored at `-300%`/`-50%` of the frame, placing the right-shifted rectangle — not the image center — over the frame

#### Scenario: Every small-avatar surface shares the zoom mapping
- **WHEN** the same URL-bearing entry with a well-formed rectangle is rendered by the switcher pill thumbnail, a switcher popover row thumbnail, and a party drawer avatar
- **THEN** all three apply the shared zoom mapping to that entry's rectangle, and a nonidentity `stage` triple on the entry changes none of them

#### Scenario: A null or malformed rectangle falls back to the centered crop
- **WHEN** any surface in the small-avatar set receives null, `undefined`, a non-finite field, an out-of-bounds field, an edge-crossing rectangle, or non-positive width/height
- **THEN** the image renders with no zoom properties — the centered `50% 50%` cover crop — and nothing throws

#### Scenario: A placeholder entry renders no image
- **WHEN** a switcher row or party drawer avatar carries a null-URL placeholder entry, whatever its rectangle field says
- **THEN** the existing labelled or glyph placeholder renders with no image element, identical to the pre-change behavior

#### Scenario: A whole-image rectangle zooms to identity
- **WHEN** a small avatar renders an entry whose rectangle is `{x: 0, y: 0, w: 1, h: 1}`
- **THEN** the mapping produces 100% sizing at zero offsets and the frame shows the same centered cover crop as before

#### Scenario: A degenerate skinny rectangle clamps at the cap
- **WHEN** a small avatar renders an entry whose rectangle has a width or height below 1/8 of the image (e.g. `{x: 0.49, y: 0.49, w: 0.02, h: 0.02}`)
- **THEN** the enlargement clamps to 800% on that axis, the anchor offset is derived from the clamped factor (e.g. `-392%`/`-392%`), and nothing throws
