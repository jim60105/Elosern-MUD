# official-art-personalization Specification

## Purpose
Define personalization of read-only official artwork: the entity-local explicit official-image selection (with its mutual clearing against the runtime gallery default), personal geometry overrides keyed by the stable root-relative image identity with update-tolerant degradation, and the backend-authoritative read-only guarantees that keep every official mutation attempt from touching shared files or another character's state.

## Requirements

### Requirement: A personal official selection is an entity-local art preference
An entity SHALL be able to explicitly select one official image — identified by its stable root-relative identity within its content reference — as a personal art preference stored on the entity's own art state. The selection SHALL replace the personal gallery-default choice in presentation step 1: a selected-and-resolving official image presents ahead of the gallery default card, while equipment-bound runtime cards retain their existing precedence. Setting an explicit runtime gallery default SHALL clear the personal official selection, and setting a personal official selection SHALL clear the explicit runtime default, so exactly one personal default governs. The selection SHALL NOT edit the mounted directory, SHALL NOT create or modify a gallery card, and SHALL NOT change any other entity's presentation.

#### Scenario: Explicit official selection presents ahead of the runtime default
- **WHEN** a subject holds a gallery default card and explicitly selects a valid official image from its content reference
- **THEN** the official image presents (official origin), the gallery default card still exists unchanged, and a matching equipment-bound card would still outrank both

#### Scenario: Selections clear each other
- **WHEN** a subject with a personal official selection sets a runtime gallery default, and another subject with a runtime default selects an official image
- **THEN** each ends with exactly one personal default and presents accordingly

#### Scenario: Selection touches no shared state
- **WHEN** a player selects an official image
- **THEN** the mounted directory bytes are unchanged, no card is appended to `GalleryRecord.cards`, and no other entity's presentation changed

### Requirement: Stale official selections are retained but ignored for resolution
When a personal official selection names an identity the catalog no longer resolves (removed by an update, refused by admission, or content-directory absent), image resolution SHALL ignore the selection and continue through the remaining chain (runtime default, classic, official default, silhouette) while RETAINING the preference; no resolution failure SHALL delete the preference or any image. A selection whose identity still exists SHALL resolve its updated bytes after a maintenance restart — same identity, new content, no re-selection required.

#### Scenario: Removed image falls through, preference survives
- **WHEN** the official image a player selected disappears from a later prepared directory and the server restarts
- **THEN** presentation falls through to the remaining chain, the stored preference remains, and no runtime card was affected

#### Scenario: Same identity resolves new bytes after restart
- **WHEN** an operator replaces the bytes at the selected identity's path and the server restarts
- **THEN** the retained selection presents the new bytes under the same identity with a refreshed cache fingerprint, and the player's selection state is unchanged

### Requirement: Official-image geometry overrides are personal, identity-keyed, and update-tolerant
A character's face-rectangle and stage-placement adjustment for an official image SHALL be stored as a personal override keyed by that image's stable root-relative identity, written through the existing art-preference writer and validated with the existing geometry rules against the image's current decoded dimensions. Overrides SHALL be entity-local: one character's adjustment never changes another's display or the directory metadata. If an artwork update makes a stored override invalid for the image's current dimensions, rendering SHALL use valid directory metadata or the fitted default geometry, the preference SHALL be retained, and one bounded diagnostic SHALL be emitted.

#### Scenario: Two characters, same bytes, different geometry
- **WHEN** two preset-born characters select the same official image and each sets a different rectangle and stage triple
- **THEN** each renders its own override and the mounted source plus each other's state are unchanged

#### Scenario: An update invalidates a stored override gracefully
- **WHEN** an artwork update replaces an image at smaller dimensions and a stored personal rectangle no longer validates against it
- **THEN** rendering uses metadata or fitted-default geometry, one bounded diagnostic is logged, the preference remains stored, and no other character's rendering changed

### Requirement: Official mutation attempts fail named, with no file or shared change
Backend mutation surfaces SHALL reject attempts to delete, replace, regenerate-overwrite, bind, or otherwise mutate an official image entry by its official identity, each with a named stable rejection and zero side effects: no file written or deleted under the official root, no gallery card changed, no preference cleared. The frontend SHALL hide or disable inappropriate operations, but the backend SHALL remain the authority and the rejection SHALL hold for direct requests. Manual gallery generation SHALL continue to write runtime artwork only — never into the mounted directory, never replacing an official asset file. Replacing the official directory (a maintenance update) SHALL NOT delete runtime cards, clear player selections, or import copies into any gallery record.

#### Scenario: Delete attempt on an official entry is refused
- **WHEN** a client dispatches a card-delete (or regenerate, or replace) request naming an official image identity
- **THEN** a stable rejection code returns, the official file, the runtime store, and every gallery record are byte-for-byte unchanged, and no preference was touched

#### Scenario: Generation never writes official bytes
- **WHEN** manual generation settles for a subject whose content reference has official artwork
- **THEN** the new card lives under the runtime gallery identity only and the official directory is unchanged

#### Scenario: An update preserves all personal state
- **WHEN** an operator swaps the prepared directory between two versions and restarts
- **THEN** generated cards, runtime selections, personal official selections, and geometry overrides all remain exactly as before
