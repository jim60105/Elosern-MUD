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
- **WHEN** (after personalization lands) a subject with a `done` classic asset explicitly selects a resolving official image and later clears the selection
- **THEN** the selected official image presents while set and the classic asset presents again after clearing, with no mutation by either act — the outranking was the player's decision, not a catalog default replacing runtime art

#### Scenario: Artwork updates never switch runtime images to official defaults
- **WHEN** official artwork is replaced or added for a subject whose image was player-selected or generated
- **THEN** that player-selected or generated image keeps presenting — the update never switches it to an official default

#### Scenario: The personal selection is exempt by construction
- **WHEN** the personal official selection added by `official-art-personalization` is set
- **THEN** it is exempt from the catalog-default protection by construction — it is itself the player's explicit choice, presented at the personal-default slot ahead of the classic asset exactly as design §7 orders it, and clearing it restores the pre-selection resolution unchanged with nothing mutated by either act

#### Scenario: Bare registry subject uses its own official reference
- **WHEN** a registered scene or monster typed subject is resolved without an entity
- **THEN** the same registered content reference is used by presentation and automatic suppression; no character reference is guessed from its stable key
