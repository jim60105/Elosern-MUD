## MODIFIED Requirements

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints before sampling a magic
value, then atomically write the trait configuration, identity attributes, sampled starting magic
level, active state, and creation-owned initial mechanical state: `magic_xp`, skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit. If any write fails, it
SHALL restore all persisted and in-process trait state and leave the character pending. Activation
SHALL not create or puppet an object, and SHALL not change the shell's dbref, account relation, or
puppeting.

The relocation to the starting location is a separate, best-effort step taken only after the atomic
activation commit succeeds. It SHALL move the shell to 聖潔王都南門 (`capital_altoria` `(2,0)`), SHALL
NOT advance the world clock and SHALL NOT emit a player-move event, and SHALL NEVER roll back the
already-committed activation when it fails. If the starting location does not exist, the shell SHALL
remain in place, activation SHALL still succeed, and the player SHALL receive a degradation notice
instead of the arrival welcome.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes, and
  magic-progress attributes, with no active command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_level` trait

#### Scenario: Activation moves the shell to the starting location
- **WHEN** a valid activation commits for an already puppeted pending shell and the 南門 room exists
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are unchanged,
  its location is the 聖潔王都南門 room, and the relocation does not advance the world clock

#### Scenario: Activation succeeds even when the starting location is unavailable
- **WHEN** a valid activation commits but the 南門 room does not exist
- **THEN** activation still succeeds, the pending gate is still removed, the shell remains in place,
  and the player receives a degradation notice rather than the arrival welcome

#### Scenario: A failed relocation never rolls back activation
- **WHEN** a valid activation commits but the relocation fails for any reason
- **THEN** the activation remains committed and the player remains able to play from wherever the
  shell is
