# Spec Delta

## MODIFIED Requirements

### Requirement: Companions follow the player through every exit traversal

The follow function in the party module SHALL resolve the commander from the traverser — the player character itself, or the owner of a possessed companion puppeted by the owner's account — and SHALL move every other party member present in the source room (the commander's own body when the traverser is a possessed companion, and every effective companion other than the traverser) to the traverser's destination, and SHALL be invoked from every exit success path. Companion movement SHALL charge no world clock, SHALL emit no announce messages, SHALL leave the party binding unchanged, and SHALL never raise from any traversal hook.

#### Scenario: Companions follow a successful grid traversal
- **WHEN** a player with two companions in the source room traverses an ordinary or grid exit
- **THEN** both companions' locations equal the player's new location, the player's clock advance is unchanged by their movement, and the party binding is unchanged

#### Scenario: Companions follow through the wilderness gate
- **WHEN** a player with companions in the grid room enters the wilderness through a gate exit
- **THEN** each companion arrives at that gate's `approach_cell` through the provider API (the same cell the player landed on — never a footprint cell), and the player's clock advance reflects only the player's `wilderness_move` cost

#### Scenario: Companions follow an ordinary wilderness step
- **WHEN** a player with companions in the same wilderness room steps to a neighboring coordinate
- **THEN** each companion moves to the player's new coordinates through the provider API with no additional clock charge

#### Scenario: Companions follow the wilderness return to the grid
- **WHEN** a player with companions in the wilderness returns through the registered gate
- **THEN** each companion arrives in the grid room with the player and no additional clock charge occurs

#### Scenario: A companion move failure leaves the companion behind
- **WHEN** a destination rejects one companion's move
- **THEN** that companion stays at its current location, the player receives the 跟丟了 notification naming it, the other companions still follow, and no state other than the notification changes

#### Scenario: Follow never charges the clock
- **WHEN** a player with companions traverses any exit
- **THEN** the world clock advances by exactly the player's movement cost, with no additional advance attributable to the companions

#### Scenario: An empty party traverses with no side effects
- **WHEN** a player with no companions traverses an exit
- **THEN** the traversal behaves exactly as before this change and no notification is emitted

#### Scenario: A bound companion in another room is not pulled
- **WHEN** a player whose companion is in a different room traverses an exit
- **THEN** the companion's location is unchanged and no notification is emitted

#### Scenario: Non-exit relocation does not pull companions
- **WHEN** a player is relocated by a teleport, spawn, or other non-exit move
- **THEN** the companions' locations are unchanged

#### Scenario: A stale party entry never blocks follow
- **WHEN** the player's party list contains the dbid of a deleted NPC
- **THEN** the follow skips the stale entry, the remaining companions still follow, and no exception is raised

#### Scenario: A left-behind companion rejoins on a later traversal
- **WHEN** a companion failed to follow and the player later traverses an exit from the companion's current room
- **THEN** the companion follows on that traversal and the player receives no repeated notification

#### Scenario: Every exit success path invokes follow
- **WHEN** an exit traversal succeeds
- **THEN** follow is invoked from the shared `MovementCostMixin.at_post_traverse` hook (grid, instance, and base exits), the wilderness gate entry branch (`WildernessGateExit.at_traverse`), the wilderness return branch, and the ordinary wilderness step branch (`WildernessReturnExit.at_traverse`)

#### Scenario: Companion moves use the traversal-appropriate move API
- **WHEN** companions follow through any exit type
- **THEN** grid and instance destinations are reached through quiet `move_to`, and wilderness entry and wilderness steps move companions through the wilderness provider's coordinate API (`enter_wilderness` / `script.move_obj`), never through a plain `move_to` into a wilderness room

#### Scenario: One fixed left-behind notification names every companion per traversal
- **WHEN** one or more companions' follow moves fail in a traversal
- **THEN** each failed companion remains at its current location and the player receives one fixed Traditional Chinese 「跟丟了」 notification per traversal naming every companion left behind

#### Scenario: Follow triggers only on exit paths
- **WHEN** the player is relocated by a teleport, spawn, or other non-exit move, or a bound companion waits in a different room
- **THEN** follow does not trigger: companions are not pulled, and a bound companion in a different room is not teleported to the player

#### Scenario: The whole party follows a possessed traversal
- **WHEN** the player possesses 艾拉 and walks her through an exit while the player's own body and companion 卡恩 share her source room
- **THEN** the player's body and 卡恩 arrive in 艾拉's destination through the same follow moves, with no additional clock charge and the party and possession bindings unchanged

#### Scenario: The owner body follows quietly and stays entranced
- **WHEN** the player's own body follows a possessed traversal
- **THEN** it moves with a quiet `move_to` (or the wilderness provider API), records the destination in the commander's map knowledge, keeps its entranced presentation and its possession mirror, and is never puppeted by the move

#### Scenario: Party members stay together under possession
- **WHEN** the player, while possessing a companion, traverses several exits in a row with every follow succeeding
- **THEN** after each traversal the commander's body and every effective companion share the traverser's room
