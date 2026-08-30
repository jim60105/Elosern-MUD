## MODIFIED Requirements

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints, then atomically write
the trait configuration (including the allocated `magic_power` static), identity attributes,
active state, and creation-owned initial mechanical state: skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit. If any write fails, it
SHALL restore all persisted and in-process trait state and leave the character pending. Activation
SHALL not create or puppet an object, and SHALL not change the shell's dbref, account relation, or
puppeting.

The relocation to the starting location is a separate, best-effort step taken only after the atomic
activation commit succeeds. It SHALL move the shell to 聖潔王都南門 (`capital_altoria` `(2,0)`), SHALL
NOT advance the world clock and SHALL NOT emit a player-move event, and SHALL NEVER roll back the
already-committed activation when it fails. It SHALL additionally record the South Gate's canonical
`grid:capital_altoria:2:0` node through `world.rules.map_knowledge.record_arrival()` (the
`map-knowledge` capability) without charging movement time, so a freshly activated character starts
with the starting location known on their minimap. If the starting location does not exist, the shell
SHALL remain in place, activation SHALL still succeed, the player SHALL receive a degradation notice
instead of the arrival welcome, and no map-knowledge observation SHALL be recorded.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes, and
  initial mechanical attributes, with no active command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_power` trait

#### Scenario: Activation moves the shell to the starting location and records it
- **WHEN** a valid activation commits for an already puppeted pending shell and the 南門 room exists
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are unchanged,
  its location is the 聖潔王都南門 room, the relocation does not advance the world clock, and its
  map-knowledge record contains the `grid:capital_altoria:2:0` node

#### Scenario: Activation succeeds even when the starting location is unavailable
- **WHEN** a valid activation commits but the 南門 room does not exist
- **THEN** activation still succeeds, the pending gate is still removed, the shell remains in place,
  the player receives a degradation notice rather than the arrival welcome, and no map-knowledge
  observation is recorded

#### Scenario: A failed relocation never rolls back activation and records nothing
- **WHEN** a valid activation commits but the relocation fails for any reason
- **THEN** the activation remains committed, the player remains able to play from wherever the
  shell is, and no map-knowledge observation is recorded
