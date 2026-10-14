# Spec Delta

## MODIFIED Requirements

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

