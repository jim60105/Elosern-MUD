## Purpose

The browser's graphical art surface: an exact read-only `art` panel available in
exploration and combat modes, a validated scene payload with truthful
placeholders, a server-authored age-checked portrait catalog, client-local
contextual portrait focus, targeted worker-completion pushes, deterministic
offline degradation, and keyboard-first desktop-bounded browser acceptance.

## Requirements

### Requirement: The art panel is an exact read-only panel available in exploration and combat modes
The production presentation registry SHALL register `art` schema version 4. Its available payload
SHALL contain exactly `schema_version`, `available`, `kind`, `scene`, and `portrait_catalog`;
`available` SHALL be true and `kind` SHALL be `scene`. The panel SHALL be available in `exploration`
and `combat` modes and SHALL use the registered common unavailable form in `creation` mode.

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

#### Scenario: Presenter reads state strictly and mutates none
- **WHEN** the presenter builds the `art` payload
- **THEN** it strictly reads the authenticated puppet's current location and (in combat) its
  active combat session, and mutates no traits, resources, buffs, sexual state, combat session,
  map knowledge, quests, location, art records, or world time

#### Scenario: The payload carries no reference, path, or rejected content
- **WHEN** the presenter emits the `art` payload
- **THEN** it contains no live object reference, no filesystem path, no store root, and no
  rejected prompt content

#### Scenario: Portrait wire and all readers cut over together
- **WHEN** art schema 3 and roster schema 3 ship
- **THEN** portrait_catalog values and roster portraits carry the complete canonical artwork descriptor plus authorized display context; active validators and every portrait consumer reject the old flat image fields while scene retains its prior shape until its separately versioned cutover

#### Scenario: Both artwork vocabularies are canonical
- **WHEN** art schema 4 is shipped
- **THEN** scene is exactly {archetype, label, alt, artwork} with the canonical scene descriptor; portrait_catalog retains the complete canonical portrait values from schema 3; server/client validators and all scene consumers switch atomically and old scene image fields are rejected

### Requirement: The scene payload resolves only validated archetypes with truthful placeholders
The scene payload SHALL carry the current logical scene identity and room-aware canonical descriptor through the shared art resolver. Source order SHALL be authored room official, generated archetype, optional operator type official, required bundled type official and distinct terminal. Missing/pending generation SHALL use normal bundled art; reached failures SHALL persist without writes or roots exposure.

#### Scenario: Done scene serves the same-origin media URL
- **WHEN** the generated archetype source is done and no higher room source succeeds
- **THEN** the generated candidate has its validated same-origin URL and independent done state; the renderer follows canonical precedence

#### Scenario: Pending scene retains a labelled prior image
- **WHEN** generation is pending for the same scene and generation subject with an applicable prior success
- **THEN** the prior good image is retained until same/higher-priority replacement; a different scene discards it immediately

#### Scenario: Failed, missing, or invalid scene uses the gradient stage and placeholder label
- **WHEN** generation is failed, missing, disabled or its selected file disappeared
- **THEN** shared resolution tries type/terminal art; expected absence has no error and reached failure remains visible, with non-image background only at exhaustion

#### Scenario: The scene renders as the full-bleed stage backdrop
- **WHEN** the client renders a resolved scene
- **THEN** it renders as the full-bleed stage backdrop with cover-style cropping, and displays the
  scene label and alternative text as text outside the bitmap

#### Scenario: A pending scene with a prior image dims and labels it
- **WHEN** the same scene and generation subject is pending with retained good art
- **THEN** the image remains with factual pending explanation and no error styling; no prior-place art can be retained

#### Scenario: No prior image degrades to the gradient stage
- **WHEN** a fresh scene has no retained success
- **THEN** its own required type/terminal art is provisionally available while higher sources resolve, without mode-based sample selection

### Requirement: The portrait catalog is server-authored, age-checked, and bounded
The portrait catalog SHALL be bounded, deterministic and keyed by opaque identities admitted to the current visible/focusable art view; owned roster portraits remain independently scoped and do not expand this catalog. Each value SHALL carry the complete canonical descriptor and bounded display context. Existing named-policy/canonical-age checks and monster visual-species provenance SHALL remain. Ineligible subjects SHALL expose no real candidate or generated subject key.

#### Scenario: Combat catalog mirrors the context_actions participants
- **WHEN** combat presentation resolves participants and the art panel resolves its portrait catalog
- **THEN** the two panels share the same participant identities, and each present participant maps to
  exactly one catalog value keyed by that identity

#### Scenario: A named present character resolves to a verified portrait value
- **WHEN** an authorized named-policy character passes canonical-age checks
- **THEN** its descriptor carries truthful generation and ordered source facts with no client-built key or URL

#### Scenario: A generic monster shares one portrait per bestiary archetype
- **WHEN** a present monster has registered visual-species provenance
- **THEN** its entry resolves portrait:monster:<visual-key> with only that species runtime or official artwork; missing images carry monster_anon and context remains keyed by opaque entity identity

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

#### Scenario: The catalog carries no canonical or non-present data
- **WHEN** the catalog payload is inspected
- **THEN** it carries only currently present focusable identities and contains no persona text,
  disguised stats, combat resources, or any subject that is not currently present

#### Scenario: A resolved catalog entry carries its face rectangle
- **WHEN** a present entity resolves to a gallery image
- **THEN** its catalog entry carries a media URL and a face rectangle of exactly `x`, `y`, `w`, `h` in `[0, 1]`

#### Scenario: A placeholder entry carries a null face rectangle
- **WHEN** a subject has no real candidate
- **THEN** real geometry is absent; its separate alpha terminal geometry remains available

#### Scenario: A placeholder row can still carry the attribute-selected decorative silhouette
- **WHEN** an admitted dialogue host has no real image or named portrait policy
- **THEN** its descriptor carries the deterministic attribute-selected alpha terminal, without creating policy, gallery record or job

#### Scenario: A resolved real row retains the decorative reference
- **WHEN** a subject has real candidate attempts
- **THEN** its separate alpha terminal remains available for browser failure and does not change generation truth

#### Scenario: Catalog entries name their image origin
- **WHEN** real image candidates and a silhouette terminal occur in the descriptor
- **THEN** each resource carries its server-authored origin independently of generation state

#### Scenario: An official-backed entry carries no mutable state claim
- **WHEN** a catalog entry resolves an official image for a subject whose gallery is empty
- **THEN** the entry presents the official media and origin, the subject's gallery state remains empty, and the payload reports no generated-portrait completion

#### Scenario: Catalog membership follows the mode
- **WHEN** the portrait catalog resolves
- **THEN** in combat mode its keys are the combat-session participant identities, and in
  exploration mode the dialogue hosts, explicit named-portrait-policy characters, and live party
  companions of the player character present in the current room

#### Scenario: Every media-bearing entry names its authored origin
- **WHEN** a descriptor contains media resources
- **THEN** each candidate/terminal names its authored origin without URL inference

#### Scenario: Stage carries the exact bounded triple or null
- **WHEN** a real portrait candidate or alpha terminal is described
- **THEN** each carries its applicable geometry separately; malformed stored stage uses safe identity geometry with an attributed metadata fault

#### Scenario: The face rectangle is bounded for images and null for placeholders
- **WHEN** portrait candidate geometry is serialized
- **THEN** its face rectangle is the exact validated bounded mapping; no-real-candidate state has no real geometry and retains separate terminal geometry

#### Scenario: The catalog carries no detection, crop, or second image
- **WHEN** a descriptor is inspected
- **THEN** it contains ordered original resources and terminal metadata without face detection, pre-cropped pixels or unrelated private images

#### Scenario: Subject resolution dispatches by entity kind
- **WHEN** a present entity portrait is resolved
- **THEN** characters retain explicit named policy and canonical-age validation; monsters resolve declared visual-species provenance without a character-age gate, and unresolvable monsters retain monster_anon without a fabricated subject

#### Scenario: Eligibility is never inferred
- **WHEN** the server decides portrait eligibility for an entity
- **THEN** eligibility is not inferred from display name, key shape, or LLM authorship

#### Scenario: The canonical-age check gate rejects before any job
- **WHEN** a character's `age` or `apparent_age` is missing or malformed (non-integer)
- **THEN** the canonical-age check rejects the character and the rejected subject appears as the
  unavailable placeholder with no subject key, no URL, and no prompt content, and is not enqueued
  and never reaches a worker

### Requirement: Contextual portrait focus is client-local and verified
The browser SHALL maintain contextual portrait focus entirely client-side: the KeyboardRouter SHALL
emit a focus event and the art renderer SHALL select a supplied catalog value, and there SHALL be no
focus mutation message and no client-constructed subject key, URL, status, or alternative text. Menu
descriptors SHALL reference catalog entries by their opaque IDs.

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

#### Scenario: A full snapshot preserves focus only across a surviving ID
- **WHEN** a full snapshot replaces the catalog
- **THEN** it preserves the current focus only when the focused catalog ID survives the
  replacement; otherwise exploration has no portrait focus and combat selects the first valid
  target in deterministic presenter order

#### Scenario: A focused character with a missing portrait keeps a card
- **WHEN** the focused character has no portrait
- **THEN** the browser shows the portrait placeholder card rather than removal

#### Scenario: Descriptor supply is split across delivery units
- **WHEN** catalog-referencing menu descriptors are accounted for
- **THEN** this delivery unit supplies the combat descriptors (its `portrait_ref`), while
  exploration-menu descriptors that reference the same catalog arrive with the exploration-menu
  delivery unit

### Requirement: Worker completion pushes a targeted art panel update

Canonical requirement ID: `webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update`.

When an art-worker asset or gallery job settles and emits `asset_completed`,
the `world/art/` settle path SHALL emit a bounded server-side notification
carrying only the completed subject key. The presentation layer SHALL publish
all qualifying freshly rendered panels together in one affected-panel
`ui_update` at a newer revision per session per notification.

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

#### Scenario: Each eligible session re-renders independently

- **WHEN** a completion notification is processed for each connected WebClient session with an active puppet and an already-attached coordinator
- **THEN** the presentation layer independently re-renders `art`, `gallery`, and `roster` from that session's current canonical state and current owned presentation selection

#### Scenario: Each available panel qualifies independently

- **WHEN** freshly rendered panels are evaluated against the completed subject key
- **THEN** art qualifies when its current scene subject or any portrait-catalog entry references that key, gallery when its rendered `selected` equals that key, and roster when any rendered character row's portrait subject key equals that key
- **AND** gallery rail membership alone does not qualify a gallery update, and roster qualification is not limited to the current puppet or characters present in its room

#### Scenario: Publication proceeds without art and omits unavailable panels

- **WHEN** art does not qualify or is unavailable while another panel qualifies
- **THEN** the update publishes anyway, unavailable panels are omitted independently without suppressing another qualifying panel, and existing mode-coherence companion panels remain permitted
- **AND** when no panel qualifies nothing is published and revision does not advance

#### Scenario: Late completions gate on fresh references only

- **WHEN** a completion notification is evaluated for staleness
- **THEN** it is gated on the freshly rendered current references rather than remembered selections, rooms, sent payloads, or completed image identities; a completion for an old room, vanished entity, or no-longer-selected gallery does not replace that panel's current content or restore an old selection, and a different panel still referencing the same subject remains eligible

#### Scenario: Completion rendering is pure presentation

- **WHEN** completion rendering runs
- **THEN** it mutates no canonical state, selects no card, and sets no default, while room or present-entity-set changes continue to replace the art payload through ordinary presentation updates

#### Scenario: Delivery stays reactor-side and leak-free

- **WHEN** the completion notification is delivered
- **THEN** it remains on the existing reactor-side notification path, not the worker thread, exposes no output paths, prompts, or worker internals, and the `world/art/` package remains free of any `web/` import

#### Scenario: A missed notification is repaired, not replayed

- **WHEN** a completion notification is missed by a session
- **THEN** reconnect's current-store full snapshot repairs the view without replaying the missed push

#### Scenario: A current exploration portrait completion refreshes nullable descriptors
- **WHEN** the completed subject appears in the freshly rendered current portrait catalog, the session is exploring, and its available exploration descriptors previously had null refs because that portrait lacked real imagery
- **THEN** one newer update includes qualifying art/gallery/roster panels and the freshly rendered exploration panel, whose admitted target/entity refs now name the real catalog image, without another gameplay or focus action

#### Scenario: Scene completion does not refresh unrelated exploration descriptors
- **WHEN** only the current scene references the completed subject and no current portrait-catalog value names it
- **THEN** the completion adds no exploration panel solely for that scene, preserving targeted publication

#### Scenario: A portrait completion outside exploration keeps existing publication
- **WHEN** the session is outside exploration or its exploration panel is unavailable
- **THEN** qualifying art/gallery/roster publication continues without a fabricated exploration panel

#### Scenario: Late portrait completion cannot revive a departed target
- **WHEN** the entity left or the session changed room before a portrait completion and no current art/gallery/roster reference qualifies
- **THEN** no stale exploration descriptor is published and no revision is advanced for that completion

### Requirement: Art degradation never blocks gameplay or leaks rejected content
Image generation/service or source failures SHALL degrade presentation without blocking deterministic gameplay. Expected absence SHALL use approved normal artwork fallback; unexpected reached failures SHALL remain local after fallback. Player/OOB explanations SHALL contain no traceback, filesystem root, credential or rejected prompt. Browser-only failures SHALL not imply backend telemetry.

#### Scenario: Offline art never blocks play
- **WHEN** image generation and LLM services are unavailable and scheduler is disabled
- **THEN** movement, dialogue, combat, trades and quests proceed; correct alpha figures/name initials/bundled scene art remain, with expected absence free of error styling

#### Scenario: Image load failure degrades to fallback
- **WHEN** a rendered scene source fails load/decode
- **THEN** ordered resolution tries the next source and preserves a local failure indication without unchanged-descriptor retries

#### Scenario: Rejected content stays out of every error surface
- **WHEN** an art or presentation error occurs
- **THEN** no OOB message or panel payload contains a traceback, filesystem path, rejected prompt, or
  rejected-subject data

#### Scenario: The missing-scene placeholder gate observes a single node
- **WHEN** a missing-generation scene rerenders
- **THEN** bounded shared waits observe its committed descriptor and single successful bundled image, rather than enforcing an obsolete placeholder

#### Scenario: Every enumerated failure degrades presentation only
- **WHEN** generation is disabled or failed, a completed output is missing/invalid, data becomes unavailable, or browser loading fails
- **THEN** each leaves gameplay usable; independent failure facts stay distinct from expected absence and backend boundary diagnostics use the facade

#### Scenario: A browser image load failure stops refetching
- **WHEN** a browser source load fails
- **THEN** its version is not requested again on unchanged rerender; a new applicable revision or fresh page may retry, with persistent reached error meanwhile

#### Scenario: A degraded scene shows one labelled placeholder
- **WHEN** an image chain exhausts
- **THEN** one safe non-image state and persistent accessible failure explanation appears without a broken image

#### Scenario: The placeholder gate uses the shared bounded wait helper
- **WHEN** a scene acceptance test spans Vue replacement
- **THEN** it uses the committed canonical panel and a single visible current-scene/failure DOM readiness descriptor within one bounded deadline

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the backdrop's scene control or Enter on that focused
control and SHALL close on Escape. The scene label and alternative text SHALL remain visible as
text outside the bitmap, alternative text SHALL be meaningful, and no required information SHALL
exist only inside an image.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene control and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the stage renders at 1451x790 and at 2560x1440
- **THEN** the backdrop, the scene label and alternative text, the portrait presentation (including the stage actors), and the status text remain visible and non-overlapping

#### Scenario: Player-authored text is not executed as markup
- **WHEN** a display name or label contains HTML-like player text
- **THEN** the browser renders it as literal text and creates no element or script from it

#### Scenario: Catalog entries render only inside consuming surfaces
- **WHEN** the browser renders portrait catalog entries
- **THEN** they render only inside the framed-portrait surfaces that consume them — the party strip and
  party drawer, the stage actors that stand the dialogue host, the combat party and the combat
  foes, the interact target avatars and dock
  target rows
- **AND** the client renders no standalone portrait catalog strip and no per-portrait full-view
  control

#### Scenario: Labels are text and motion is reducible
- **WHEN** server-authored labels render and the player prefers reduced motion
- **THEN** labels are inserted as text, not trusted HTML, and reduced-motion preference disables
  nonessential transitions

#### Scenario: Both viewports keep the stage usable
- **WHEN** the stage renders at 1451x790 and at 2560x1440
- **THEN** the stage backdrop and the framed portraits remain usable without the backdrop
  covering the scene label, the HUD islands, or required status

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

#### Scenario: A well-formed rectangle centers its face region
- **WHEN** a framed portrait renders a catalog entry whose rectangle is `{x: 0.25, y: 0.06, w: 0.5, h: 0.5}`
- **THEN** the image element's object-position centers that rectangle's center (vertically the 31% line), and the image keeps its cover fit

#### Scenario: A malformed rectangle degrades to the centered crop
- **WHEN** the mapping receives null, a non-finite field, an out-of-bounds field, an edge-crossing rectangle or non-positive width/height
- **THEN** it returns centered `50% 50%`, a URL-bearing surface renders that centered cover crop and a null-URL placeholder renders its label without an image

#### Scenario: Every framed portrait honors the carried rectangle
- **WHEN** the same entry is rendered by the party strip, party drawer avatar thumbnails, dialogue host avatar, interact target avatar, dock target row and character switcher
- **THEN** each cover-cropped image applies the shared mapping to its face rectangle, even when the entry carries a nonidentity stage triple

#### Scenario: The surfaces outside the recenters-only list are unchanged by this split
- **WHEN** a gallery card, the gallery detail rail preview, or a ReferenceArtwork cover-mode image renders an entry with a well-formed rectangle
- **THEN** it still renders the recenters-only `object-position` treatment exactly as before — the small-avatar zoom-crop requirement names it in neither its surface set nor its fallbacks

#### Scenario: A malformed rectangle returns the centered pair
- **WHEN** the mapping receives a `null` or `undefined` rectangle, or any rectangle with a
  non-finite field, a field outside `[0, 1]`, an `x + w` greater than 1, a `y + h` greater than 1,
  or a non-positive `w` or `h`
- **THEN** it returns the centered `50% 50%` pair — never a throw and never an off-frame
  percentage — so one corrupt card cannot blank a portrait surface

#### Scenario: Malformed-rectangle entries still render truthfully
- **WHEN** a URL-bearing entry's rectangle is missing or malformed, or an entry is a placeholder
  (a null URL)
- **THEN** the URL-bearing entry still renders its image with the centered crop, and only the
  placeholder entry renders its labelled placeholder with no image element

#### Scenario: The small-avatar set is refined by its dedicated requirement
- **WHEN** the small-avatar set — the top-bar character switcher's thumbnails and the party
  drawer's avatar thumbnails — crops a portrait
- **THEN** it additionally obeys the dedicated small-avatar zoom-crop requirement, which refines
  this rule for those surfaces by enlarging the crop around the same rectangle while keeping the
  identical validation set and the identical centered-crop fallback
- **AND** every other surface named here keeps the recenters-only treatment verbatim

#### Scenario: Avatar surfaces apply the mapping and ignore stage
- **WHEN** each avatar surface — the party strip and the party
  drawer's avatar thumbnails, the dialogue host avatar in the narrative feed, the interact target
  avatars and the dock's target rows, and the top-bar character switcher — renders an entry
- **THEN** it applies the mapping to that entry's rectangle and ignores stage

#### Scenario: The excluded surfaces stay outside the cover rule
- **WHEN** the drawer's full-figure art slot renders, or a scene backdrop renders
- **THEN** the drawer slot uses the separate stage render contract and is excluded from this cover
  rule, and scene backdrops — consuming scene media, not portrait entries — are outside this
  requirement

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The shared figure frame SHALL consume canonical load state in both cover and stage layouts. Both SHALL use the deterministic alpha silhouette when no real portrait succeeds, preserving identity, real-versus-silhouette geometry and accessible state. Layout modes SHALL not disable silhouette policy. The manifest-listed Core/ReferenceArtwork family and coverage gate SHALL remain.

#### Scenario: A resolved entry renders the cropped image
- **WHEN** cover mode receives an entry with a media URL and a well-formed rectangle
- **THEN** it renders exactly that URL cover-fitted with the shared rect crop and no placeholder

#### Scenario: The drawer full figure consumes stage while avatars retain face crops
- **WHEN** the drawer art slot and avatar thumbnails receive the same URL-bearing portrait with stage `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** the drawer figure uses contain/bottom alignment, scale 0.6 and frame offsets 10%/-20%, while avatar cover crops remain face_rect-driven and unchanged

#### Scenario: A placeholder entry renders no image
- **WHEN** either figure layout has no successful real portrait
- **THEN** an admitted alpha terminal is observed through the shared lifecycle and drawn only after success; absent/failed alpha leaves identity text

#### Scenario: A stage silhouette is the attribute-selected alpha mask
- **WHEN** a stage-mode entry carries the server-resolved fallback identity for, respectively, an adult male, adult female, boy, girl, elder, and monster subject
- **THEN** the frame renders each committed image's own alpha mask as the dark silhouette at the current stage position — floor-aligned, aspect-preserved, unstretched — with name and state labels outside the mask, and the former inline SVG is no longer rendered

#### Scenario: A silhouette is not a completed portrait
- **WHEN** pending or failed generation reaches a healthy alpha terminal
- **THEN** the mask is available while generation stays pending/failed; only a reached failed job has persistent error styling and no generated-success claim is made

#### Scenario: A failed load degrades and a URL change recovers
- **WHEN** a real source fails then a new descriptor version repairs it
- **THEN** resolution advances through ordered attempts and alpha terminal, retains reached failure, and successful repaired version can recover

#### Scenario: A failed bundled mask keeps the frame usable
- **WHEN** the fallback mask resource itself fails to load in stage mode
- **THEN** the frame retains the actor name and the truthful text placeholder, and targeting/focus interaction remains usable

#### Scenario: The drawer full-figure slot uses stage mode
- **WHEN** the drawer's full-figure art slot renders a portrait
- **THEN** it explicitly uses stage mode instead of cover mode: contain fit, center-bottom
  positioning and bottom-center stage scale/translation, without a face_rect crop

#### Scenario: Placeholders and load outcomes degrade per mode
- **WHEN** missing/pending/failed artwork reaches either figure layout
- **THEN** both layouts use their applicable shared alpha/text result and truthful independent generation state without caller-local failure flags

#### Scenario: The stage silhouette replaces the inline standing SVG as an alpha mask
- **WHEN** a stage-mode placeholder renders its silhouette
- **THEN** the attribute-selected built-in silhouette renders in place of the former inline
  standing SVG: the server-carried fallback media identity (see `art-gallery-fallback`) drawn as a
  CSS alpha mask of the committed built-in image — mask semantics explicit, RGB texture never
  displayed, aspect ratio preserved, the figure aligned to the stage floor, filled with the
  existing dark silhouette styling

#### Scenario: Identity, interaction, and motion stay outside the decorative mask
- **WHEN** a stage-mode frame renders its silhouette
- **THEN** the actor's name, targeting/focus behavior, and the accessible missing/pending/failed
  labels render outside the decorative mask, and the pending shimmer and reduced-motion behavior
  are retained

#### Scenario: No identity never revives the legacy figure
- **WHEN** either mode receives no catalog entry or stage mode receives no admitted fallback identity
- **THEN** it renders truthful name and state text only, without a standing humanoid SVG, guessed bitmap, mask URL or subject key

#### Scenario: Failed species imagery uses its authoritative monster fallback
- **WHEN** a monster species image fails to load while its entry carries monster_anon
- **THEN** stage mode renders that committed alpha mask with a load-failure state; a failed mask leaves text only and a new species URL can recover without remount

#### Scenario: Alpha resource failure never makes a rectangle
- **WHEN** the observed alpha terminal fails
- **THEN** no mask fill is rendered, identity text remains and a persistent local indication explains the failure

### Requirement: Resolved artwork carries stage without changing asset or placeholder truth
Resolved gallery-card portraits SHALL carry validated card stage. A malformed stored stage reaching presentation SHALL degrade to `{scale: 1.0, x: 0.0, y: 0.0}` with one bounded `art_stage_invalid` warning carrying the subject. Placeholders SHALL carry null stage.

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

#### Scenario: Non-card assets carry identity stage
- **WHEN** classic done assets, fallback portraits, or scene assets resolve
- **THEN** each carries identity stage

#### Scenario: Producers and consumers retain the stage shape
- **WHEN** gallery/art/roster portrait production and stage/dialogue actor consumption run
- **THEN** they retain this stage shape, with exact Python and dependency-free Node validators
  deployed together

#### Scenario: Scenes ignore stage and dialogue hosts need no new field
- **WHEN** a scene renders, or a dialogue host references the art catalog
- **THEN** scene rendering ignores stage, and no new dialogue-host field is required

### Requirement: Small avatar thumbnails zoom-crop their portrait image to the carried face rectangle through one shared pure function
The small-avatar set — the top-bar character switcher's collapsed-pill thumbnail, its popover's
per-row thumbnails, and the party drawer's per-companion avatar image — SHALL crop a URL-bearing
portrait through one shared pure mapping exported by `web/webclient-app/components/face-rect.js`:
enlarge the image to `1/w` × `1/h` of the frame, anchored at `-x/w`/`-y/h` of the frame, so the
face rectangle (extents w, h) substantially fills the frame.

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

#### Scenario: A legacy non-square rectangle still fills without blanking
- **WHEN** the zoom renders a legacy or hand-authored non-square rectangle
- **THEN** the same enlarge-and-anchor composition fills the frame from the rectangle while
  cropping a bounded sliver on the overflowing axis, and never blanks the image — the exact window
  holds for the pixel-square rectangle the authoring path enforces

#### Scenario: The zoom validates with the shared well-formedness set
- **WHEN** the zoom mapping validates a rectangle
- **THEN** it uses exactly the same well-formedness set as the recenters-only mapping — rejecting
  `null`, `undefined`, non-finite fields, fields outside `[0, 1]`, `x + w` or `y + h` greater than
  1, and non-positive `w` or `h` — and for any rejected rectangle it produces no zoom properties,
  leaving the image to render the same centered `50% 50%` cover crop it rendered before this
  requirement

#### Scenario: Placeholder avatars and stage are untouched
- **WHEN** a small avatar receives a placeholder entry (a null URL), or an entry carrying `stage`
- **THEN** the placeholder renders its existing label or glyph placeholder with no image element,
  unchanged, and the mapping ignores `stage`

#### Scenario: The zoom is presentation-only
- **WHEN** the client zoom-crops a portrait
- **THEN** the server stores rectangles verbatim and does not crop, resize, or derive any second
  image

#### Scenario: Shared avatar loading uses the actual successful candidate
- **WHEN** the first image fails and a different source succeeds
- **THEN** all avatar surfaces use that successful source face rectangle, ignore stage placement and retain reached faults

#### Scenario: Name fallback never requests alpha resources
- **WHEN** no real avatar image succeeds
- **THEN** the first trimmed-name grapheme or neutral empty-name symbol renders without a silhouette request

### Requirement: Combat portrait references and catalog are committed coherently
A publication that starts combat SHALL include the current participant descriptors and their freshly rendered art catalog in one authoritative revision. Subsequent actions, round playback and reconnect SHALL preserve opaque participant identity and authoritative species artwork or monster_anon, without tier art or browser-derived sources.

#### Scenario: First goblin engage has no artwork
- **WHEN** a real wilderness goblin is engaged and no goblin-specific image exists
- **THEN** the first combat commit contains its catalog entry carrying monster_anon and the stage renders that mask without an intervening humanoid figure

#### Scenario: Species artwork exists before engagement
- **WHEN** that goblin has admitted goblin-specific official or runtime artwork
- **THEN** the first combat catalog carries and renders that artwork, never a same-tier other-species image

#### Scenario: Actions and completion retain species identity
- **WHEN** rounds, targeted artwork completion or reconnect update an active goblin
- **THEN** its opaque reference remains joined to goblin-specific artwork or monster_anon, never a retired tier image

#### Scenario: A terminal round retains only its decorative actor artwork
- **WHEN** committed mode leaves combat while prior foe beats still play
- **THEN** retained foe actors keep their last admitted catalog artwork for playback until release; current scene identity and canonical mode remain current, and skip, flush or epoch reset releases retained actors
