## ADDED Requirements

### Requirement: Companions follow the player through every exit traversal
The follow function in the party module SHALL move every companion of the traversing player who
is present in the source room to the player's destination, and SHALL be invoked from every exit
success path: the shared `MovementCostMixin.at_post_traverse` hook (grid, instance, and base
exits), the wilderness gate entry branch (`WildernessGateExit.at_traverse`), the wilderness
return branch, and the ordinary wilderness step branch (`WildernessReturnExit.at_traverse`).
Companion movement SHALL charge no world clock, SHALL emit no announce messages, SHALL leave the
party binding unchanged, and SHALL never raise from any traversal hook. Grid and instance
destinations SHALL be reached through quiet `move_to`; wilderness entry and wilderness steps SHALL
move companions through the wilderness provider's coordinate API (`enter_wilderness` /
`script.move_obj`), never through a plain `move_to` into a wilderness room. A companion whose move
fails SHALL remain at its current location and the player SHALL receive one fixed Traditional
Chinese 「跟丟了」 notification per traversal naming every companion left behind. Follow SHALL
trigger only on the exit paths above; teleports, spawns, and other non-exit relocations SHALL NOT
pull companions, and a bound companion in a different room SHALL NOT be teleported to the player.

#### Scenario: Companions follow a successful grid traversal
- **WHEN** a player with two companions in the source room traverses an ordinary or grid exit
- **THEN** both companions' locations equal the player's new location, the player's clock advance
  is unchanged by their movement, and the party binding is unchanged

#### Scenario: Companions follow through the wilderness gate
- **WHEN** a player with companions in the grid room enters the wilderness through the gate exit
- **THEN** each companion arrives at the entry wilderness coordinates through the provider API,
  and the player's clock advance reflects only the player's `wilderness_move` cost

#### Scenario: Companions follow an ordinary wilderness step
- **WHEN** a player with companions in the same wilderness room steps to a neighboring coordinate
- **THEN** each companion moves to the player's new coordinates through the provider API with no
  additional clock charge

#### Scenario: Companions follow the wilderness return to the grid
- **WHEN** a player with companions in the wilderness returns through the registered gate
- **THEN** each companion arrives in the grid room with the player and no additional clock charge
  occurs

#### Scenario: A companion move failure leaves the companion behind
- **WHEN** a destination rejects one companion's move
- **THEN** that companion stays at its current location, the player receives the 跟丟了
  notification naming it, the other companions still follow, and no state other than the
  notification changes

#### Scenario: Follow never charges the clock
- **WHEN** a player with companions traverses any exit
- **THEN** the world clock advances by exactly the player's movement cost, with no additional
  advance attributable to the companions

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
- **THEN** the follow skips the stale entry, the remaining companions still follow, and no
  exception is raised

#### Scenario: A left-behind companion rejoins on a later traversal
- **WHEN** a companion failed to follow and the player later traverses an exit from the
  companion's current room
- **THEN** the companion follows on that traversal and the player receives no repeated
  notification
