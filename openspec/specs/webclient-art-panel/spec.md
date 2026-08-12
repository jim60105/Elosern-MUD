## Purpose

The browser's graphical art surface: an exact read-only `art` panel available in
exploration and combat modes, a validated scene payload with truthful
placeholders, a server-authored adult-gated portrait catalog, client-local
contextual portrait focus, targeted worker-completion pushes, deterministic
offline degradation, and keyboard-first desktop-bounded browser acceptance.

## Requirements

### Requirement: The art panel is an exact read-only panel available in exploration and combat modes
The production presentation registry SHALL register `art` schema version 1. Its available payload
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
explanatory label otherwise. The scene SHALL use the 16:9 area with cover-style cropping and SHALL
display its label and alternative text outside the bitmap. When the current scene is pending and a
prior scene is already rendered, the panel SHALL retain that prior image visibly dimmed and labelled
`目前場景圖片生成中`; without a prior image, and for failed or invalid assets, it SHALL use the scene
placeholder. The panel SHALL NOT silently present old art as current, SHALL NOT expose `out_path` or
the store root, and SHALL derive its URL only from a validated stored identity.

#### Scenario: Done scene serves the same-origin media URL
- **WHEN** a room's scene archetype has a `done` asset record with an existing validated output
- **THEN** the scene payload carries the asset status, the same-origin `/art/...` URL, 16:9 aspect,
  and meaningful alternative text, and never an absolute filesystem path

#### Scenario: Pending scene retains a labelled prior image
- **WHEN** the current scene is pending and a prior scene image is already rendered
- **THEN** the panel keeps that prior image dimmed with the explicit `目前場景圖片生成中` label and the
  pending status rather than presenting it as current art

#### Scenario: Failed, missing, or invalid scene uses the placeholder
- **WHEN** the scene asset is failed, missing, scheduler-disabled, or its output file is absent
- **THEN** the scene payload is the scene placeholder with its truthful label and no URL, and no
  stale image is substituted

### Requirement: The portrait catalog is server-authored, adult-gated, and bounded
The art panel `portrait_catalog` SHALL be a bounded object keyed by the opaque IDs of currently
present focusable entities: the combat-session participant identities in combat mode, and the
dialogue hosts and explicit named-portrait-policy characters present in the current room in
exploration mode, in deterministic order. Each catalog value SHALL contain the server-resolved
subject key, asset status, same-origin media URL or placeholder, aspect ratio, alternative text, and
bounded display context (name plus role/target label). Portrait subject resolution SHALL dispatch by
entity kind: a named character SHALL resolve `portrait:character:<stable-key>` only from an explicit
named `portrait_policy` through the adult gate; a generic monster SHALL resolve
`portrait:monster:<archetype>` from its bestiary `MONSTER_TIER_REGISTRY` archetype without any
character age gate; and anything else SHALL be the unavailable placeholder. Eligibility SHALL NOT be
inferred from display name, key shape, or LLM authorship. The adult gate SHALL reject a character
when either `age` or `apparent_age` is missing, malformed, or below 18; a rejected subject SHALL
appear as the unavailable placeholder with no subject key, no URL, and no prompt content, and SHALL
NOT be enqueued or reach a worker. The catalog SHALL contain only currently present focusable
identities and SHALL NOT contain persona text, disguised stats, combat resources, or any subject that
is not currently present.

#### Scenario: Combat catalog mirrors the context_actions participants
- **WHEN** combat presentation resolves participants and the art panel resolves its portrait catalog
- **THEN** the two panels share the same participant identities, and each present participant maps to
  exactly one catalog value keyed by that identity

#### Scenario: A named present character resolves to a verified portrait value
- **WHEN** a present character carries an explicit named portrait policy and passes the adult gate
- **THEN** its catalog entry carries the resolved subject key and status, a same-origin URL or
  truthful placeholder, and its display context, and no browser-constructed key or URL exists

#### Scenario: A generic monster shares one portrait per bestiary archetype
- **WHEN** a present monster carries a valid bestiary `threat_tier`
- **THEN** its catalog entry resolves `portrait:monster:<threat_tier>` with the archetype-shared asset
  or its placeholder, and its name and role context are keyed by the opaque entity identity

#### Scenario: An underage canonical age never reaches the browser payload as a prompt
- **WHEN** a present character's canonical `age` equals 17
- **THEN** its catalog entry is the unavailable placeholder with no subject key and no URL, and the
  worker fixture records zero jobs and zero worker invocations for that subject

#### Scenario: An underage apparent age never reaches the browser payload as a prompt
- **WHEN** a present character's canonical `apparent_age` equals 17 while `age` is adult
- **THEN** its catalog entry is the unavailable placeholder with no subject key and no URL, and the
  worker fixture records zero jobs and zero worker invocations for that subject

#### Scenario: Missing or malformed age values reject without a prompt
- **WHEN** a present character's `age` or `apparent_age` is missing, non-integer, or otherwise
  malformed
- **THEN** the subject resolves to the unavailable placeholder, nothing is enqueued, and no prompt,
  subject key, or URL is produced

#### Scenario: Non-present entities are excluded
- **WHEN** a room contains entities that are not present (e.g. in another room) or carry no explicit
  named policy and are not dialogue hosts
- **THEN** none of them appears in the portrait catalog

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
prompt content.

#### Scenario: Offline art never blocks play
- **WHEN** the worker command is fixed to fail and the scheduler is disabled
- **THEN** the player can move, talk, fight, trade, and turn in quests while the art panel shows only
  placeholders and no gameplay action waits on a job

#### Scenario: Image load failure degrades to fallback
- **WHEN** a rendered scene URL fails to load in the browser
- **THEN** the panel shows its fallback text/placeholder and does not repeatedly refetch the same URL

#### Scenario: Rejected content stays out of every error surface
- **WHEN** an art or presentation error occurs
- **THEN** no OOB message or panel payload contains a traceback, filesystem path, rejected prompt, or
  underage subject data

### Requirement: Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded
The scene full view SHALL open by click on the image or Enter on the focused image and SHALL close on
Escape; the portrait SHALL have its own accessible full-view control. The scene label and alternative
text SHALL remain visible outside the bitmap, alternative text SHALL be meaningful, and no required
information SHALL exist only inside an image. Server-authored labels SHALL be inserted as text, not
trusted HTML, and reduced-motion preference SHALL disable nonessential transitions. The 16:9 scene
and 3:4 portrait SHALL remain usable at both 1440x900 and 1280x720 without covering the scene label
or required status.

#### Scenario: Keyboard-only full view opens and closes
- **WHEN** the player focuses the scene image and presses Enter, then Escape
- **THEN** the full view opens on Enter and closes on Escape with focus restored

#### Scenario: Both supported viewports keep art usable
- **WHEN** the art panel renders at 1440x900 and at 1280x720
- **THEN** the scene, its label and alternative text, the portrait overlay, and the status text remain
  visible and non-overlapping

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
