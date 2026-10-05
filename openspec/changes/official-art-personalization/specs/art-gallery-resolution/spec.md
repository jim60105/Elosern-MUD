## MODIFIED Requirements

### Requirement: Display resolution is one deterministic chain from equipment to fallback
`world/art/gallery_match.py` SHALL resolve the image shown for a subject by exactly this ordered
chain, with no other input: (1) compute the entity's four-slot equipment snapshot from stored state,
with accessories sorted and an empty slot legal; (2) keep every card whose `binding` is not `None`
and whose snapshot value for EVERY masked slot equals the computed snapshot value for that slot;
(3) among those, the card whose mask covers the most slots wins, and a tie is broken by the newest
`created_at`; (4) otherwise the personal official selection when one is set and resolves to a valid
catalog entry (see the `official-art-personalization` capability), else the card named by
`default_image_id`; (5) otherwise, when no personal official selection resolved, the subject's
classic `done` asset record, resolved exactly as it is today; (6) otherwise the official default for
the entity's official content reference (see the `official-art-resolution` capability), resolved from
the startup official snapshot — an entity with no reference, or a reference the snapshot does not
hold, falls through with no diagnostic beyond the bounded catalog vocabulary; (7) otherwise the
terminal fallback seam; (8) otherwise the existing truthful placeholder. The chain SHALL be a pure
function of stored state plus the startup official snapshot: the same record, preference, and
equipment SHALL always resolve to the same image, and no step SHALL perform a network call,
filesystem write, job enqueue, or record mutation.

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
