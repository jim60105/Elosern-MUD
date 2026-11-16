# Spec Delta

## MODIFIED Requirements

### Requirement: Activation is an all-or-nothing deterministic-core operation
The creation command SHALL submit a validated request to a deterministic `world.rules` creation
service. The service SHALL preflight all fields and allocation constraints, then atomically write
the trait configuration (including the allocated `magic_power` static), identity attributes,
active state, and creation-owned initial mechanical state: skill proficiency,
skills, equipment, inventory, wallet, quest log, guild rank, and guild merit.

#### Scenario: An activation write failure leaves no partially initialized character
- **WHEN** a test injects a failure at any activation write position after preflight
- **THEN** the character has its original pending state, trait data, identity attributes,
  initial mechanical attributes, location, `home`, and map-knowledge record, with no active
  command set enabled

#### Scenario: Successful activation enables normal gameplay exactly once
- **WHEN** a valid activation commits
- **THEN** the pending gate is removed, the normal character command set is available, and a
  subsequent `rest 5s` reaches the world clock with a real `magic_power` trait

#### Scenario: Successful activation leaves the shell in place
- **WHEN** a valid activation commits for an already puppeted pending shell
- **THEN** its dbref, `account.characters` membership, and current puppet relationship are
  unchanged and the world clock does not advance; its only change of location is the
  start-room placement

#### Scenario: A failed activation restores all trait state
- **WHEN** any activation write fails
- **THEN** the service SHALL restore all persisted and in-process trait state and leave the character pending

#### Scenario: Activation never creates or puppets an object
- **WHEN** activation succeeds for a pending shell
- **THEN** it creates no new object and puppets nothing, and the shell's dbref, account relation, and puppeting are untouched

#### Scenario: Activation performs no relocation
- **WHEN** activation succeeds wherever the shell was created
- **THEN** activation performs no relocation other than the single start-room placement, and
  records exactly one map-knowledge observation, for that start room

## ADDED Requirements

### Requirement: Activation places the character in its subrace's start room
Activation SHALL resolve the start room of the validated subrace before its first write, and fail with a creation error and no state change when resolution fails. Inside the same all-or-nothing transaction it SHALL move the character into that room, set `home` to it, and record the arrival in map knowledge, all before starting companions are built. Preset and custom activation SHALL follow the same rule.

#### Scenario: Custom activation lands in the start room
- **WHEN** a custom activation for a synthetic subrace commits
- **THEN** the character stands in that subrace's resolved start room and its `home` is that room

#### Scenario: Preset activation lands in the preset subrace's start room
- **WHEN** a preset activation commits
- **THEN** the character stands in the resolved start room of the preset's subrace and its `home` is that room

#### Scenario: The arrival is recorded in map knowledge
- **WHEN** an activation commits into a start room that is a grid room
- **THEN** the character's map-knowledge record holds that room's canonical node id with the current world tick

#### Scenario: Starting companions join in the start room
- **WHEN** a preset that declares starting companions activates
- **THEN** every built companion stands in the same start room as the player and is bound to the player's party

#### Scenario: An unresolvable start room fails before any write
- **WHEN** start-room resolution fails for the validated subrace
- **THEN** activation raises a creation error, and the character stays pending, in its original location, with its original `home`, traits and attributes

#### Scenario: A failure after the move returns the character without move hooks
- **WHEN** an injected failure happens after the move, and the birth room refuses ordinary character arrivals
- **THEN** the character is back in its birth room with its original `home` and no map-knowledge record, and the birth room's refusal does not block the return
