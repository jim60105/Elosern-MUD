# Delta: player-character-creation

## MODIFIED Requirements

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints, then atomically write
the trait configuration (including the allocated `magic_power` static), identity attributes,
active state, and creation-owned initial mechanical state: skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit. If any write fails, it
SHALL restore all persisted and in-process trait state and leave the character pending. Activation
SHALL not create or puppet an object, and SHALL not change the shell's dbref, account relation, or
puppeting. Activation performs no relocation: the shell stays wherever it was created (its 虛境
birth location), and no map-knowledge observation SHALL be recorded by activation itself.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes, and
  initial mechanical attributes, with no active command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_power` trait

#### Scenario: Successful activation leaves the shell in place
- **WHEN** a valid activation commits for an already puppeted pending shell
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are
  unchanged, its location is unchanged (the 虛境 birth room), the world clock does not advance,
  and no map-knowledge observation is recorded
