## MODIFIED Requirements

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
