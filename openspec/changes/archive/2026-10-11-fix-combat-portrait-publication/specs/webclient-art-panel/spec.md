# Spec Delta

## MODIFIED Requirements

### Requirement: The reference artwork frame presents a portrait entry truthfully through cover fit and rect crop
The ReferenceArtwork component SHALL retain separate cover and stage modes. Its cover mode SHALL
render one URL-bearing image with the shared face_rect crop. The component SHALL remain
manifest-listed as Core/ReferenceArtwork in the frozen required set and covered by the
deterministic coverage gate.

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

#### Scenario: The drawer full-figure slot uses stage mode
- **WHEN** the drawer's full-figure art slot renders a portrait
- **THEN** it explicitly uses stage mode instead of cover mode: contain fit, center-bottom
  positioning and bottom-center stage scale/translation, without a face_rect crop

#### Scenario: Placeholders and load outcomes degrade per mode
- **WHEN** a null entry or placeholder entry (null URL) reaches either mode, an image load fails,
  or the frame receives a changed URL
- **THEN** a null or placeholder entry renders its truthful labelled placeholder with no image, a
  failed load degrades to that mode's labelled placeholder, and a changed URL re-attempts the new
  image without remounting the surface

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

## ADDED Requirements

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

