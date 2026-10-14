# Spec Delta

## MODIFIED Requirements

### Requirement: The art panel is an exact read-only panel available in exploration and combat modes
The production presentation registry SHALL register `art` schema version 3. Its available payload
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

