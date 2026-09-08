## ADDED Requirements

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
A monster subject SHALL resolve by skipping steps 1 through 3 of the chain: the default card, then
the classic asset record, then the fallback seam, then the placeholder. No equipment snapshot SHALL
be computed for a monster subject and no monster card SHALL be selected by a binding.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: A monster with no card falls through unchanged
- **WHEN** a monster subject holds no card and its classic asset record is `done`
- **THEN** the classic asset is resolved exactly as it is today

### Requirement: The chain ends at one fallback seam
`world/art/gallery_match.py` SHALL expose exactly one terminal seam `fallback_for(subject)` consulted
after the classic asset record and before the placeholder. In this capability the seam SHALL return
`None`, so the chain's terminal behaviour is byte-for-byte today's placeholder. A later capability
MAY supply a fallback without modifying the chain.

#### Scenario: The seam returning nothing preserves today's placeholder
- **WHEN** nothing resolves for a subject and the seam returns `None`
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
- **WHEN** a resolved card's stored rectangle fails validation
- **THEN** the payload carries the shared default rectangle and one bounded diagnostic is logged

### Requirement: Gallery URLs are built only from validated card identities
The presenter SHALL build a gallery media URL only from a card's stored identity that it has
validated against the subject's own `gallery/<kind>/<subject-key>/` prefix, the closed set of store
extensions, and the store-root confinement check (rejecting symlinks and out-of-root resolutions). A
card whose file no longer exists or fails validation SHALL be skipped by the chain, which SHALL
continue to the next step rather than emit a broken URL. The presenter SHALL never expose an absolute
path or the store root.

#### Scenario: A card whose file vanished is skipped, not emitted
- **WHEN** the resolved card's file has been deleted from the store
- **THEN** the chain continues to the next step and the payload never carries that card's URL

#### Scenario: A cross-subject or out-of-root identity is never served
- **WHEN** a card carries an identity whose path segments address a different subject, or that resolves outside the store root or through a symlink
- **THEN** the card is skipped and no URL is produced from it
