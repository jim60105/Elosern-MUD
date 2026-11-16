## MODIFIED Requirements

### Requirement: An unbound card is never auto-selected
Unbound cards SHALL be eligible only as the explicit gallery default. With no matching binding or named default, resolution SHALL continue through official selection/default and declared terminal sources without choosing an unselected card.

#### Scenario: Unbound cards with no default are not shown
- **WHEN** a subject holds only unbound cards and `default_image_id` is `None`
- **THEN** the chain resolves past them to the official default, declared terminal or placeholder

#### Scenario: An unbound card set as default is shown
- **WHEN** an unbound card is the subject's `default_image_id` and no binding matches
- **THEN** that card is resolved

## ADDED Requirements

### Requirement: All artwork subjects use the gallery-only deterministic chain
Every gallery-bearing subject SHALL use one read-only deterministic chain of stored state and startup snapshots. Order SHALL be matching binding where declared, explicit official selection, gallery default, official catalog default, declared terminal, then non-image placeholder. Kind differences SHALL come only from capabilities; authored room overrides remain outside and ahead of the subject chain.

#### Scenario: The most specific matching binding wins
- **WHEN** one card binds `armor` alone and another binds `armor` and `weapon_main`, and the entity's current equipment matches both
- **THEN** the two-slot card is resolved

#### Scenario: An equal-specificity tie resolves to the newest card
- **WHEN** two cards bind the same slot set and both match the current equipment
- **THEN** the card with the newest `created_at` is resolved

#### Scenario: A binding over empty slots matches an unequipped entity
- **WHEN** a card binds `armor` with an empty snapshot value and the entity wears no armour
- **THEN** that card matches and is a candidate

#### Scenario: Changing equipment changes the resolved card
- **WHEN** the entity's armour changes from the item one card's binding names to the item another card's binding names
- **THEN** the resolved card changes accordingly with no write to any gallery record

#### Scenario: A personal official selection replaces the gallery default
- **WHEN** a subject has a set personal official selection that resolves and a `default_image_id` card, and no binding matches
- **THEN** the selected official image resolves at step 4 and the default card is consulted only if the selection fails to resolve

#### Scenario: A stale selection falls to the default card
- **WHEN** the personal official selection names an identity the snapshot does not hold and a default card exists
- **THEN** the default card resolves at step 4 and the preference remains stored

#### Scenario: No match falls through to the default
- **WHEN** no binding matches, no official selection is set, and a default is set
- **THEN** the default card is resolved

#### Scenario: A runtime card outranks an available official default
- **WHEN** a subject resolves a gallery default card and its content reference has official artwork in the snapshot
- **THEN** the card is resolved and the official step is never consulted

#### Scenario: Nothing runtime falls through to the official default
- **WHEN** no binding matches, no official selection or default card exists, the entity's content reference has a valid catalog entry
- **THEN** the official default resolves ahead of the fallback seam

#### Scenario: Step 1 computes the equipment snapshot
- **WHEN** the chain runs step 1
- **THEN** it computes the entity's four-slot equipment snapshot from stored state, with accessories
  sorted and an empty slot legal

#### Scenario: Step 2 keeps every fully matching bound card
- **WHEN** the chain runs step 2
- **THEN** it keeps every card whose `binding` is not `None` and whose snapshot value for EVERY
  masked slot equals the computed snapshot value for that slot

#### Scenario: Step 3 picks the most specific mask, newest on a tie
- **WHEN** the chain runs step 3 among the matching cards
- **THEN** the card whose mask covers the most slots wins, and a tie is broken by the newest
  `created_at`

#### Scenario: Step 4 takes the personal official selection, else the default card
- **WHEN** the chain reaches step 4
- **THEN** it takes the personal official selection when one is set and resolves to a valid catalog
  entry (see the `official-art-personalization` capability), else the card named by
  `default_image_id`

#### Scenario: Official position resolves the official default or falls through
- **WHEN** the chain reaches the official position
- **THEN** it takes the official default for the entity's official content reference (see the
  `official-art-resolution` capability), resolved from the startup official snapshot, and an entity
  with no reference, or a reference the snapshot does not hold, falls through with no diagnostic
  beyond the bounded catalog vocabulary

#### Scenario: Terminal position consults the terminal fallback seam
- **WHEN** the chain reaches the terminal position
- **THEN** it consults the terminal fallback seam

#### Scenario: Placeholder position ends at the truthful placeholder
- **WHEN** the chain reaches the placeholder position with nothing resolved
- **THEN** it produces the existing truthful placeholder

#### Scenario: Failures keep their source position
- **WHEN** an explicit selection/default source cannot resolve
- **THEN** the canonical internal attempts retain its bounded fault before remaining candidates, while first valid candidate selection preserves existing deterministic policy and no mutation occurs

#### Scenario: Scene and portrait share precedence
- **WHEN** scene, monster and character subjects each have a generated default and an unselected official default
- **THEN** each selects the generated default through the same chain; selecting official explicitly makes official win unless a declared binding matches

#### Scenario: Scene envelope retains room priority
- **WHEN** a scene target declares a valid room override and its archetype has a generated default
- **THEN** the room override remains first; removing it exposes the archetype chain without changing its shared preferences

### Requirement: Declared binding support gates shared resolution
Every kind SHALL skip binding reads and selection unless its capability declares binding support. The remaining chain SHALL be identical across kinds, with preference ownership and terminal policy declared in capabilities. A non-binding kind SHALL never compute an equipment snapshot.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: The binding steps follow the declaration
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** the binding steps are skipped and no equipment snapshot is computed, with no edit to the resolution module

#### Scenario: A tier-keyed monster falls through the official step
- **WHEN** a monster has no resolvable visual provenance, regardless of its combat tier
- **THEN** no tier subject or card is read; monster_anon is carried without an equipment, age or personal-state write

#### Scenario: The binding steps are steps 1 through 3
- **WHEN** the declaration-gated steps are named
- **THEN** they are steps 1 through 3 — the equipment snapshot, the binding candidates, and the
  most-specific-mask selection

#### Scenario: No snapshot and no binding selection for a non-binding kind
- **WHEN** resolution runs for a kind whose declaration does not support bindings
- **THEN** no equipment snapshot is computed for such a subject and no card of such a subject is
  selected by a binding

#### Scenario: Monster official defaults await the species catalog
- **WHEN** a monster has validated complete-species or baseline visual provenance
- **THEN** its own registered visual species official default can resolve; an absent package falls through only to monster_anon after same-species runtime resolution fails

#### Scenario: Tier records cannot outrank a species default
- **WHEN** a species has an official image while its monster's tier has an unauthorized old gallery image on disk
- **THEN** those tier records are never read or applied and the species image resolves

#### Scenario: A redeclared kind changes selection policy
- **WHEN** a synthetic gallery-bearing kind declares no bindings and subject-scoped official preferences
- **THEN** it resolves official selection, gallery default and official default without equipment or entity-age reads

### Requirement: Gallery and official resources carry their own geometry
Each original portrait candidate and alpha terminal SHALL carry its own validated face rectangle in resource geometry. Card pixel-square and fallback anchor semantics SHALL remain. Scene geometry SHALL have null face rectangle. Geometry SHALL remain placement-only metadata without server cropping, transforms or second images.

#### Scenario: A resolved card carries its own rectangle
- **WHEN** a card with explicit rectangle becomes a canonical candidate
- **THEN** that candidate geometry carries its own validated rectangle and admitted URL

#### Scenario: A placeholder carries a null rectangle
- **WHEN** no real portrait candidate exists
- **THEN** no real geometry is fabricated; separately admitted alpha terminal keeps its own rectangle

#### Scenario: A malformed stored rectangle degrades to the default
- **WHEN** stored card rectangle is malformed or nonsquare
- **THEN** safe fitted candidate geometry is used with an attributed metadata fault and bounded diagnostic

#### Scenario: An official payload carries validated metadata geometry
- **WHEN** an official default with a valid declared manifest rectangle and a non-identity declared stage resolves
- **THEN** the payload carries that rectangle validated against the image's decoded dimensions, and that declared stage — the identity triple only when none is declared or it is invalid

#### Scenario: A card payload carries its own validated rectangle
- **WHEN** a card resolves
- **THEN** the payload carries the resolved card's normalized rectangle, validated through the
  gallery face-rect validator against that card's recorded `image_size`

#### Scenario: A fallback payload carries the seam's rectangle
- **WHEN** a fallback image resolved
- **THEN** the payload carries the rectangle the fallback seam supplies, defaulting to the shared
  default

#### Scenario: An official payload carries validated directory geometry
- **WHEN** an official image resolved
- **THEN** the payload carries the directory-metadata or fitted-default rectangle validated against
  the decoded image dimensions (see the `official-art-resolution` capability)

#### Scenario: Every placeholder payload carries a null rectangle
- **WHEN** no real image is described
- **THEN** there is no top-level face_rect; real geometry is absent and alpha-terminal geometry remains separate

#### Scenario: A bad stored rectangle degrades with a diagnostic, never failure
- **WHEN** stored image geometry is invalid
- **THEN** the candidate uses safe fitted/shared geometry with source-scoped metadata fault and diagnostic, rather than failing the whole descriptor

#### Scenario: All geometry locations use the exact canonical schema
- **WHEN** roster/art catalog descriptors are serialized
- **THEN** face_rect is inside each applicable resource.geometry; obsolete flat url/face_rect/stage fields fail validation

## REMOVED Requirements

### Requirement: Display resolution is one deterministic chain from equipment to fallback
**Reason**: Replaced by All artwork subjects use the gallery-only deterministic chain; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Monster subjects resolve through the chain without the binding steps
**Reason**: Replaced by Declared binding support gates shared resolution; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Every resolution payload carries a face rectangle or null
**Reason**: Replaced by Gallery and official resources carry their own geometry; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.
