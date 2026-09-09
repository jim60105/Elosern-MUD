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
chain, with no other input: (1) compute the entity's four-slot equipment snapshot from stored state,
with accessories sorted and an empty slot legal; (2) keep every card whose `binding` is not `None`
and whose snapshot value for EVERY masked slot equals the computed snapshot value for that slot;
(3) among those, the card whose mask covers the most slots wins, and a tie is broken by the newest
`created_at`; (4) otherwise the card named by `default_image_id`; (5) otherwise the subject's classic
`done` asset record, resolved exactly as it is today; (6) otherwise the terminal fallback seam;
(7) otherwise the existing truthful placeholder. The chain SHALL be a pure function of stored state:
the same record and the same equipment SHALL always resolve to the same card.

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

#### Scenario: No match falls through to the default
- **WHEN** no card's binding matches the current equipment and a default is set
- **THEN** the default card is resolved

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
The chain SHALL run steps 1 through 3 — the equipment snapshot, the binding candidates, and the
most-specific-mask selection — only for a subject kind whose capability declaration supports
bindings. A kind that does not support them, which the monster portrait kind does not, SHALL resolve
by skipping those steps: the default card, then the classic asset record, then the fallback seam, then
the placeholder. No equipment snapshot SHALL be computed for such a subject and no card of such a
subject SHALL be selected by a binding. The skip SHALL be decided by reading the declaration, never by
comparing the subject kind inline.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: A monster with no card falls through unchanged
- **WHEN** a monster subject holds no card and its classic asset record is `done`
- **THEN** the classic asset is resolved exactly as it is today

#### Scenario: The binding steps follow the declaration
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** the binding steps are skipped and no equipment snapshot is computed, with no edit to the resolution module

### Requirement: The chain ends at one fallback seam
`world/art/gallery_match.py` SHALL expose exactly one terminal seam `fallback_for(subject)` consulted
after the classic asset record and before the placeholder. The seam was introduced inert (returning
`None`, byte-for-byte today's placeholder) and is now filled by `art-gallery-fallback`: it resolves
the built-in default identity and face rectangle for person subjects and returns `None` for scene
subjects, without the chain itself being modified. The presenter threads the entity it already
resolved to the seam as an optional parameter; a bare subject-only call stays legal.

#### Scenario: The seam returning nothing preserves today's placeholder
- **WHEN** nothing resolves for a subject and the seam returns `None` (e.g. a scene subject)
- **THEN** the payload is exactly the truthful placeholder this project produces today

### Requirement: Every resolution payload carries a face rectangle or null
`world/art/presenter.py` SHALL add `face_rect` to every resolution payload it produces: the resolved
card's normalized rectangle when a card resolved, the shared default rectangle when a classic asset
resolved, the rectangle the fallback seam supplies (defaulting to the shared default) when a
fallback image resolved, and `null` for every placeholder payload. The value SHALL be a mapping
of exactly `x`, `y`, `w`, `h` in `[0, 1]`. The server SHALL NOT crop, transform, or produce a second
image: the rectangle is placement metadata for the client alone. A malformed stored rectangle SHALL
degrade to the shared default rectangle with one bounded diagnostic, never to a failed payload.

#### Scenario: A resolved card carries its own rectangle
- **WHEN** a card with an explicit rectangle resolves
- **THEN** the payload carries a URL and exactly that rectangle

#### Scenario: A placeholder carries a null rectangle
- **WHEN** the chain resolves to any placeholder
- **THEN** the payload carries a null URL and a null `face_rect`

#### Scenario: A malformed stored rectangle degrades to the default
- **WHEN** the resolution seam hands the presenter a card whose stored rectangle fails validation
- **THEN** the payload carries the shared default rectangle and one bounded diagnostic is logged

### Requirement: Gallery URLs are built only from validated card identities
The presenter SHALL build a gallery media URL only from a card's stored identity that it has
validated against the subject's own `gallery/<kind>/<subject-key>/` prefix, the closed set of store
extensions, and the store-root confinement check (rejecting symlinks and out-of-root resolutions). A
card whose file no longer exists or fails validation SHALL be skipped, with resolution continuing at
the next remaining candidate of the current step or the next step, rather than the chain emitting a
broken URL. The presenter SHALL never expose an absolute path or the store root.

#### Scenario: A card whose file vanished is skipped, not emitted
- **WHEN** the resolved card's file has been deleted from the store
- **THEN** the chain continues to the next step and the payload never carries that card's URL

#### Scenario: A cross-subject or out-of-root identity is never served
- **WHEN** a card carries an identity whose path segments address a different subject, or that resolves outside the store root or through a symlink
- **THEN** the card is skipped and no URL is produced from it

