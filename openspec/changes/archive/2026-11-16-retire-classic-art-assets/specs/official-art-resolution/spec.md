## MODIFIED Requirements

### Requirement: The extended chain stays deterministic, offline, and side-effect-free
All gallery-bearing kinds SHALL resolve from stored state and startup snapshots without network calls, writes or enqueue. Generated defaults SHALL outrank unselected official defaults; explicit official choices SHALL outrank generated defaults after any declared binding. Registry-backed references SHALL resolve from validated typed subjects even without an entity.

#### Scenario: Runtime art outranks official defaults
- **WHEN** a subject resolves a gallery default card and its content reference also has official artwork
- **THEN** the card is presented with its runtime discriminator and the official entry remains merely selectable

#### Scenario: Resolution performs no writes
- **WHEN** a hundred official-backed entities present across snapshots
- **THEN** no asset record, queue record, gallery record, stored file, or entity attribute changed

#### Scenario: The selection exemption is the player's own choice
- **WHEN** a scene subject or monster individual whose generated default remains stored selects a resolving official image and later clears that selection
- **THEN** official presents while selected and the retained generated default resolves after clearing; character mutual clearing never restores a default that the explicit selection action cleared

#### Scenario: Artwork updates never switch runtime images to official defaults
- **WHEN** official artwork is replaced or added for a subject whose image was player-selected or generated
- **THEN** that player-selected or generated image keeps presenting — the update never switches it to an official default

#### Scenario: The personal selection is exempt by construction
- **WHEN** the personal official selection added by `official-art-personalization` is set
- **THEN** the explicit choice presents at its declared personal slot; clearing resumes the chain from actual remaining stored state without restoring a cleared character default, and presentation itself writes nothing

#### Scenario: Bare registry subject uses its own official reference
- **WHEN** a registered scene or monster typed subject is resolved without an entity
- **THEN** the same registered content reference is used by presentation and automatic suppression; no character reference is guessed from its stable key
