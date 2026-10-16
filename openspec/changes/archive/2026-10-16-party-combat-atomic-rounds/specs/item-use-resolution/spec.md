# Spec Delta

## MODIFIED Requirements

### Requirement: Combat item use occupies one initiative-ordered round
An active combat session SHALL admit a preflight-valid `ItemUseRequest` as a commanded allied actor's selected
action in a complete draft. Interactive ordinary-round providers SHALL supply that request exactly once at the
selected actor's initiative position. A preflight rejection SHALL start no round. If an earlier
initiative action invalidates a preflight-valid item request, the already-started round SHALL
remain consumed without automatic retarget or item consumption. The number of targets an item reaches SHALL NOT affect the number of rounds it
consumes.

#### Scenario: Valid potion use runs one combat round
- **WHEN** an injured commanded ally has a preflight-valid healing potion selection and the complete party draft passes preflight
- **THEN** the potion request resolves at that actor's initiative position, other eligible allies receive only their single selected commands and enemies retain their ordinary configured action slots, and the session round count increases exactly once

#### Scenario: Full HP preserves the combat turn
- **WHEN** a full-HP player attempts to use a healing potion during active combat
- **THEN** preflight rejects before initiative, no participant acts, no item is consumed, and the round
  count is unchanged

#### Scenario: Mid-round invalidation consumes the started round
- **WHEN** item preflight succeeds but an earlier initiative action makes the player unable to use the
  item at their turn
- **THEN** item resolution rejects without consumption, prior actions remain committed, and the round
  count increases once

#### Scenario: Later combat failure restores item surfaces
- **WHEN** item use resolves but later upkeep, session persistence, or terminal settlement raises
- **THEN** HP, inventory, contained mirror, session state, all participant effects, and in-process
  caches roll back together, for the actor and for every entity the item touched

#### Scenario: Player-direction overwhelm uses the item once
- **WHEN** the player's team is overwhelming and an injured ally selects a valid healing potion
- **THEN** the potion waits for the complete draft, resolves once at its actor's ordinary initiative position, and no compressed automatic basic attacks replace selected allied commands

#### Scenario: A four-target item still consumes one round
- **WHEN** a player in active combat uses an item whose effects reach four combatants
- **THEN** all four are affected within one initiative position and the session round count increases
  exactly once

#### Scenario: The item request carries battlefield context and a chosen target
- **WHEN** combat admits a preflight-valid `ItemUseRequest`
- **THEN** it supplies the battlefield action context and the player's chosen target when the item's
  scope requires one

#### Scenario: The item request dispatches only to the deterministic item resolver
- **WHEN** a round provider executes the supplied item request
- **THEN** it dispatches only to the deterministic item resolver

#### Scenario: Other participants keep ordinary policy actions
- **WHEN** a round provider supplies the selected actor's item request
- **THEN** other capable allies receive only their selected commands and capable enemies retain ordinary policy actions

#### Scenario: Combat rollback covers every item surface on every touched entity
- **WHEN** a combat item use must be rolled back
- **THEN** combat's outer rollback contract includes inventory, selected mirror object, and every
  item-touched cache **on every touched entity**

#### Scenario: A combat item use contributes only round-based time
- **WHEN** an item use resolves during a combat round
- **THEN** it contributes round-based time and adds no separate item-use time

