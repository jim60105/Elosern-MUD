# art-gallery-resolution Specification

## Purpose

Define how the gallery resolves which image a subject displays: the
deterministic chain in `world/art/gallery_match.py` from the entity's
four-slot equipment snapshot through masked-binding matching to the default
card, the monster chain variant that skips the binding steps, the single
terminal fallback seam, the presenter payload `face_rect` carriage contract,
the rule that gallery media URLs are built only from validated card
identities, and the media route's admission of gallery and built-in-default
identities under the same store-root confinement discipline.

## Requirements

### Requirement: Display resolution is one deterministic chain from equipment to fallback
`world/art/gallery_match.py` SHALL resolve the image shown for a subject by exactly this ordered
chain, with no other input. The chain SHALL be a pure function of stored state plus the startup
official snapshot: the same record, preference, and equipment SHALL always resolve to the same
image, and no step SHALL perform a network call, filesystem write, job enqueue, or record
mutation.

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
- **WHEN** no binding matches, no official selection or default card exists, the classic record is absent, and the entity's content reference has a valid catalog entry
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

#### Scenario: Step 5 falls to the classic done asset record
- **WHEN** the chain reaches step 5, meaning no personal official selection resolved
- **THEN** it resolves the subject's classic `done` asset record, exactly as it is today

#### Scenario: Step 6 resolves the official default or falls through
- **WHEN** the chain reaches step 6
- **THEN** it takes the official default for the entity's official content reference (see the
  `official-art-resolution` capability), resolved from the startup official snapshot, and an entity
  with no reference, or a reference the snapshot does not hold, falls through with no diagnostic
  beyond the bounded catalog vocabulary

#### Scenario: Step 7 consults the terminal fallback seam
- **WHEN** the chain reaches step 7
- **THEN** it consults the terminal fallback seam

#### Scenario: Step 8 ends at the truthful placeholder
- **WHEN** the chain reaches step 8 with nothing resolved
- **THEN** it produces the existing truthful placeholder

### Requirement: An unbound card is never auto-selected
A card whose `binding` is `None` SHALL be eligible ONLY as the subject's explicit default. When no
binding matches the current equipment and `default_image_id` is `None`, the chain SHALL fall through
to the classic asset record, the fallback seam, and finally the placeholder — even when unbound cards
exist — so no image the player has not chosen is ever displayed as a surprise.

#### Scenario: Unbound cards with no default are not shown
- **WHEN** a subject holds only unbound cards and `default_image_id` is `None`
- **THEN** the chain resolves past them to the classic asset, fallback, or placeholder

#### Scenario: An unbound card set as default is shown
- **WHEN** an unbound card is the subject's `default_image_id` and no binding matches
- **THEN** that card is resolved

### Requirement: Monster subjects resolve through the chain without the binding steps
The chain SHALL run the binding steps only for a subject kind whose capability declaration supports
bindings. A kind that does not support them, which the monster portrait kind does not, SHALL resolve
by skipping those steps: the default card, then the classic asset record, then the official-default
step, then the fallback seam, then the placeholder. The skip SHALL be decided by reading the
declaration, never by comparing the subject kind inline.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: A monster with no card falls through unchanged
- **WHEN** a monster subject holds no card and its classic asset record is `done`
- **THEN** the classic asset is resolved exactly as it is today

#### Scenario: The binding steps follow the declaration
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** the binding steps are skipped and no equipment snapshot is computed, with no edit to the resolution module

#### Scenario: A tier-keyed monster falls through the official step
- **WHEN** a registered threat-tier monster with no species/content reference resolves with a populated official snapshot
- **THEN** the official step resolves nothing for it, no tier-to-content mapping runs, and the fallback seam presents

#### Scenario: The binding steps are steps 1 through 3
- **WHEN** the declaration-gated steps are named
- **THEN** they are steps 1 through 3 — the equipment snapshot, the binding candidates, and the
  most-specific-mask selection

#### Scenario: No snapshot and no binding selection for a non-binding kind
- **WHEN** resolution runs for a kind whose declaration does not support bindings
- **THEN** no equipment snapshot is computed for such a subject and no card of such a subject is
  selected by a binding

#### Scenario: Monster official defaults await the species catalog
- **WHEN** the monster official-default step runs today
- **THEN** it resolves only from a validated species/content reference, which no in-repo producer
  supplies before the separate monster species catalog lands (see `official-content-provenance`), so
  monster resolution today falls through the official step to the fallback seam exactly as it does
  now

### Requirement: The chain ends at one fallback seam
`world/art/gallery_match.py` SHALL expose exactly one terminal seam `fallback_for(subject)` consulted
after the classic asset record and the official-default step and before the placeholder. The
presenter threads the entity it already resolved to the seam as an optional parameter; a bare
subject-only call stays legal.

#### Scenario: The seam returning nothing preserves today's placeholder
- **WHEN** nothing resolves for a subject and the seam returns `None` (e.g. a scene subject)
- **THEN** the payload is exactly the truthful placeholder this project produces today

#### Scenario: The seam still runs when the official step resolves nothing
- **WHEN** a subject reaches the official-default step and its reference is absent from the snapshot
- **THEN** the chain consults the terminal seam exactly as before the official step existed

#### Scenario: The seam was introduced inert and is now filled
- **WHEN** the seam's history is read against `art-gallery-fallback`
- **THEN** it was introduced inert (returning `None`, byte-for-byte today's placeholder) and is now
  filled by `art-gallery-fallback`, without the chain itself being modified

#### Scenario: The filled seam serves persons and declines scenes
- **WHEN** the filled seam resolves
- **THEN** it resolves the built-in default identity and face rectangle for person subjects and
  returns `None` for scene subjects

### Requirement: Every resolution payload carries a face rectangle or null
`world/art/presenter.py` SHALL add `face_rect` to every resolution payload it produces. The value
SHALL be a mapping of exactly `x`, `y`, `w`, `h` in `[0, 1]`, and a rectangle carried from a card or
the fallback map SHALL be pixel-square on the image it ships with — every rectangle a client
receives from a resolution marks a square region of its image. The server SHALL NOT crop, transform,
or produce a second image: the rectangle is placement metadata for the client alone.

#### Scenario: A resolved card carries its own rectangle
- **WHEN** a card with an explicit rectangle resolves
- **THEN** the payload carries a URL and exactly that rectangle

#### Scenario: A placeholder carries a null rectangle
- **WHEN** the chain resolves to any placeholder
- **THEN** the payload carries a null URL and a null `face_rect`

#### Scenario: A malformed stored rectangle degrades to the default
- **WHEN** the resolution seam hands the presenter a card whose stored rectangle fails validation against the card's recorded image size — including one that is not pixel-square
- **THEN** the payload carries the fitted default square for that card's image and one bounded diagnostic is logged

#### Scenario: A classic-asset payload keeps the shared constant
- **WHEN** a classic (non-card) asset resolves
- **THEN** the payload carries the shared default constant rectangle, bounds-validated with no image size

#### Scenario: An official payload carries validated metadata geometry
- **WHEN** an official default with a valid declared manifest rectangle and a non-identity declared stage resolves
- **THEN** the payload carries that rectangle validated against the image's decoded dimensions, and that declared stage — the identity triple only when none is declared or it is invalid

#### Scenario: A card payload carries its own validated rectangle
- **WHEN** a card resolves
- **THEN** the payload carries the resolved card's normalized rectangle, validated through the
  gallery face-rect validator against that card's recorded `image_size`

#### Scenario: A classic payload carries the shared composition anchor
- **WHEN** a classic asset resolves
- **THEN** the payload carries the shared default rectangle — the card-less composition anchor, which
  knows no image size

#### Scenario: A fallback payload carries the seam's rectangle
- **WHEN** a fallback image resolved
- **THEN** the payload carries the rectangle the fallback seam supplies, defaulting to the shared
  default

#### Scenario: An official payload carries validated directory geometry
- **WHEN** an official image resolved
- **THEN** the payload carries the directory-metadata or fitted-default rectangle validated against
  the decoded image dimensions (see the `official-art-resolution` capability)

#### Scenario: Every placeholder payload carries a null rectangle
- **WHEN** the chain produces any placeholder payload
- **THEN** its `face_rect` is `null`

#### Scenario: A bad stored rectangle degrades with a diagnostic, never failure
- **WHEN** a stored rectangle is malformed or non-square for its image
- **THEN** it SHALL degrade to the fitted default square for that card's `image_size` (the shared
  default constant where no image size is known) with one bounded diagnostic, never to a failed
  payload

### Requirement: Gallery URLs are built only from validated card identities
The presenter SHALL build a gallery media URL only from a card's stored identity that it has
validated against the subject's own `gallery/<kind>/<subject-key>/` prefix, the closed set of store
extensions, and the store-root confinement check (rejecting symlinks and out-of-root resolutions).
The presenter SHALL never expose an absolute path or the store root.

#### Scenario: A card whose file vanished is skipped, not emitted
- **WHEN** the resolved card's file has been deleted from the store
- **THEN** the chain continues to the next step and the payload never carries that card's URL

#### Scenario: A cross-subject or out-of-root identity is never served
- **WHEN** a card carries an identity whose path segments address a different subject, or that resolves outside the store root or through a symlink
- **THEN** the card is skipped and no URL is produced from it

#### Scenario: An invalid card never yields a broken URL
- **WHEN** a card's file no longer exists or its identity fails validation
- **THEN** the card SHALL be skipped, with resolution continuing at the next remaining candidate of
  the current step or the next step, rather than the chain emitting a broken URL
