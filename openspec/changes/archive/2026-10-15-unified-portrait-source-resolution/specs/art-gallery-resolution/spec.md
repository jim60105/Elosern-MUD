# Spec Delta

## MODIFIED Requirements

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

#### Scenario: Failures keep their source position
- **WHEN** an explicit selection/default/classic source cannot resolve
- **THEN** the canonical internal attempts retain its bounded fault before remaining candidates, while first valid candidate selection preserves existing deterministic policy and no mutation occurs

### Requirement: The chain ends at one fallback seam
`world/art/gallery_match.py` SHALL expose exactly one terminal seam `fallback_for(subject)` consulted
after the classic asset record and the official-default step and before the placeholder. The
presenter threads the entity it already resolved to the seam as an optional parameter; a bare
subject-only call stays legal.

#### Scenario: The seam returning nothing preserves today's placeholder
- **WHEN** no person alpha terminal is admitted
- **THEN** identity text remains as the terminal non-image result; scenes use their distinct art-domain chain rather than a person silhouette

#### Scenario: The seam still runs when the official step resolves nothing
- **WHEN** a subject reaches the official-default step and its reference is absent from the snapshot
- **THEN** the chain consults the terminal seam exactly as before the official step existed

#### Scenario: The seam was introduced inert and is now filled
- **WHEN** the current person chain is read
- **THEN** one authoritative deterministic alpha selector supplies its terminal without duplicate selector or legacy aliases

#### Scenario: The filled seam serves persons and declines scenes
- **WHEN** the filled seam resolves
- **THEN** it resolves the built-in default identity and face rectangle for person subjects and
  returns `None` for scene subjects

