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
dialogue hosts and explicit named-portrait-policy characters present in the current room in
exploration mode, in deterministic order. Each catalog value SHALL contain the server-resolved
subject key, asset status, same-origin media URL or placeholder, aspect ratio, alternative text, and
bounded display context (name plus role/target label), and the resolved normalized face rectangle. The face rectangle SHALL be a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` whenever the entry carries a media URL, and SHALL be `null` whenever the entry is a placeholder, so a client never offsets a frame it has no image for. The catalog SHALL carry no face-detection result, no crop, and no second image reference. Portrait subject resolution SHALL dispatch by
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
When the external art worker completes an asset, the `world/art/` settle path SHALL emit a bounded
server-side completion notification, and the presentation layer SHALL re-render the `art` panel for
each connected WebClient session with an active coordinator and publish an affected-panel `ui_update`
at a newer revision only when that session's current scene subject or portrait catalog references the
completed subject key. A late completion for an old room or a no-longer-present entity SHALL NOT
replace the visible panel. Room or present-entity-set changes SHALL replace the art payload through
ordinary presentation updates. The notification SHALL carry the completed subject key only and SHALL
NOT expose output paths, prompts, or worker internals, and the `world/art/` package SHALL remain free
of any `web/` import.

#### Scenario: A done scene reaches sessions currently showing that scene
- **WHEN** a scene subject completes while connected sessions currently render that scene
- **THEN** each such session receives one newer `art` panel update with the done URL and no other
  panel changes

#### Scenario: A late completion never replaces the current panel
- **WHEN** a subject completes after the session moved to a different scene or the entity left
- **THEN** the completed subject does not replace the currently rendered scene or portrait, and the
  visible panel is unchanged

#### Scenario: Reconnect resolves current status from the store
- **WHEN** a browser reconnects after a completion notification was missed
- **THEN** the full snapshot renders the current asset status from the store without replaying the
  missed push

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
control and SHALL close on Escape; the portrait SHALL have its own accessible full-view control. The
scene label and alternative text SHALL remain visible as text outside the bitmap, alternative text
SHALL be meaningful, and no required information SHALL exist only inside an image. Server-authored
labels SHALL be inserted as text, not trusted HTML, and reduced-motion preference SHALL disable
nonessential transitions. The stage backdrop and the 3:4 portrait SHALL remain usable at both
1440x900 and 1280x720 without the backdrop covering the scene label, the HUD islands, or required
status.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1440x900 and at 1280x720
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation, and the status text remain visible and non-overlapping

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
the image's p% point with the
frame's p% point, which centers the rectangle's center. The mapping SHALL return the centered
`50% 50%` pair — never a throw and never an off-frame percentage — for a `null` or `undefined`
rectangle and for any rectangle with a non-finite field, a field outside `[0, 1]`, an `x + w` greater
than 1, a `y + h` greater than 1, or a non-positive `w` or `h`, so one corrupt card cannot blank a
portrait surface. A URL-bearing entry whose rectangle is missing or malformed SHALL still render its
image with that centered crop; only a placeholder entry (a null URL) SHALL render its labelled
placeholder with no image element. Each framed-portrait surface — the combat participant frame, the
party strip and party drawer, the dialogue host avatar in the narrative feed, the interact target
avatars and the dock's target rows, and the top-bar character switcher — SHALL apply the mapping to
that entry's rectangle. The 美術展示 catalog browser's own grid tiles and full view MAY use the
centered default crop; scene backdrops consume scene media, not portrait entries, and are outside
this requirement.

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's `object-position` is the pair that centers that rectangle's center (vertically the 31% line for this rectangle), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives `null`, a non-finite field, a field outside `[0, 1]`, a rectangle crossing either normalized edge, or a non-positive width or height
- **THEN** it returns the centered `50% 50%` pair, a URL-bearing surface renders that image with the centered crop, and a null-URL placeholder entry renders its labelled placeholder with no image element

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same catalog entry is rendered by the combat participant frame, the party strip and the party drawer, the dialogue host avatar, an interact target avatar, a dock target row, and the character switcher
- **THEN** each cover-cropped image applies the shared mapping to that entry's rectangle rather than a fixed center crop

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The `World/ReferenceArtwork` component SHALL render a portrait catalog entry as one cover-fitted image
whose crop follows the entry's `face_rect`, with no invented frame: a `null` entry or a placeholder
entry (null URL) SHALL render the truthfully labelled placeholder and no image element; a media load
that fails SHALL degrade that frame to the labelled placeholder; and a subsequent entry whose URL
differs SHALL re-attempt and render the new image, so a repaired asset recovers without remounting the
surface. The component SHALL be manifest-listed in the re-frozen required set and covered by the
deterministic component-coverage gate.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** the frame receives an entry carrying a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: A placeholder entry renders no image
- **WHEN** the frame receives a null entry or an entry whose URL is null with a placeholder label
- **THEN** no image element exists in the frame and the placeholder's label is the rendered text

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** a rendered entry's image fires a load error, and the frame is later given an entry with a different URL
- **THEN** the failed load replaces the image with the labelled placeholder, and the changed URL renders a new image element carrying the replacement URL
