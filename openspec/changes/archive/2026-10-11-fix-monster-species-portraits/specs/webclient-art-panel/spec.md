# Spec Delta

## MODIFIED Requirements

### Requirement: The portrait catalog is server-authored, age-checked, and bounded
The art panel `portrait_catalog` SHALL be a bounded object keyed by the opaque IDs of currently
present focusable entities, in deterministic order. Each catalog value SHALL contain the
server-resolved subject key, asset status, same-origin media URL or placeholder, aspect ratio,
alternative text, and bounded display context (name plus role/target label).

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
- **WHEN** a present entity resolves to any truthful placeholder
- **THEN** its catalog entry carries a null URL and a null face rectangle

#### Scenario: A placeholder row can still carry the attribute-selected decorative silhouette
- **WHEN** a present dialogue-host NPC with no named portrait policy and stored sex/apparent-age attributes resolves to the unavailable placeholder
- **THEN** the entry's real URL, subject key, and face rectangle are null, and its decorative `fallback` field carries the attribute-selected identity — not one shared shape for every missing actor — with no policy, gallery record, or job created for the entity

#### Scenario: A resolved real row retains the decorative reference
- **WHEN** a catalog entry resolves a real runtime image
- **THEN** the entry's real fields carry the image with the `runtime` origin and the decorative `fallback` field remains available for a browser-side load-failure re-render

#### Scenario: Catalog entries name their image origin
- **WHEN** present entities resolve an official image, a runtime card image, and a built-in silhouette respectively in one snapshot
- **THEN** each entry carries the discriminator naming its own server-resolved source, and no client-side URL inspection is needed or performed to tell them apart

#### Scenario: An official-backed entry carries no mutable state claim
- **WHEN** a catalog entry resolves an official image for a subject whose gallery is empty
- **THEN** the entry presents the official media and origin, the subject's gallery state remains empty, and the payload reports no generated-portrait completion

#### Scenario: Catalog membership follows the mode
- **WHEN** the portrait catalog resolves
- **THEN** in combat mode its keys are the combat-session participant identities, and in
  exploration mode the dialogue hosts, explicit named-portrait-policy characters, and live party
  companions of the player character present in the current room

#### Scenario: Every media-bearing entry names its authored origin
- **WHEN** a catalog entry carries a media value
- **THEN** it carries the server-authored portrait origin discriminator — the closed vocabulary
  established by `art-gallery-fallback` (`runtime | silhouette | placeholder`), extended with
  `official` (see the `official-art-resolution` capability) — so an official image, a runtime
  image, and a silhouette are distinguishable without inspecting the URL

#### Scenario: Stage carries the exact bounded triple or null
- **WHEN** a catalog entry resolves
- **THEN** stage is an exact finite bounded `{scale, x, y}` mapping for assets and null for
  placeholders, and malformed stored card stage degrades to identity rather than failing a
  snapshot

#### Scenario: The face rectangle is bounded for images and null for placeholders
- **WHEN** a catalog entry resolves
- **THEN** the face rectangle is a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]` whenever the
  entry carries a media URL, and `null` whenever the entry is a placeholder, so a client never
  offsets a frame it has no image for
- **AND** the resolved normalized face rectangle and stage triple accompany the other value
  fields

#### Scenario: The catalog carries no detection, crop, or second image
- **WHEN** the catalog payload is inspected
- **THEN** it carries no face-detection result and no crop, and — beyond the decorative
  `fallback` field established by `art-gallery-fallback` — no second image reference

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

