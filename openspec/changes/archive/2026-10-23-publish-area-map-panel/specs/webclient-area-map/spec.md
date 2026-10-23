# Spec Delta

## Purpose

Publish an on-demand whole-area map with truthful layer geometry, visited-node fog of war and adjacent-only movement descriptors.

## ADDED Requirements

### Requirement: Map view requests publish the requested area without changing gameplay
The registered map.view action SHALL accept an area scope request and publish only the requested area_map panel through existing action/panel registries. Reads SHALL not change location, clock, knowledge or quests. Maps SHALL not be automatically rebuilt or pushed on committed movement; an open client requests its active scope again.

#### Scenario: Read request is admitted through the normal dispatcher
- **WHEN** an authenticated puppeted client submits map.view with scope area
- **THEN** the normal admission/ordering path publishes area_map and leaves gameplay state unchanged

#### Scenario: Movement does not push expensive maps
- **WHEN** a move commits or a text-command snapshot refresh occurs without map.view
- **THEN** no area/world map is recomputed or newly pushed; unrelated presentation and text remain functional

### Requirement: Area maps reveal visited nodes and one-step frontier across all layers
For a grid, instance or interior map, area_map SHALL include every visited node on that map and every node adjacent to a visited node, with visibility current, visited or seen. Roads SHALL require both ends known and at least one end visited. Grid positions SHALL retain integer metre geometry; instance/interior nodes SHALL carry no coordinates. Gateway values SHALL use the minimap gateway contract. Move actions SHALL exist only for currently traversable adjacent exits.

#### Scenario: Whole visited graph is available beyond the minimap window
- **WHEN** a player has visited nodes more than two hops from the current room
- **THEN** all such visited nodes and their one-step frontier appear, but no unseen deeper dungeon/room branches or seen-to-seen roads are emitted

#### Scenario: Room graphs stay coordinate free
- **WHEN** an instance or ordinary interior is mapped
- **THEN** real canonical room IDs and exits are emitted with no invented grid/world coordinates, while current adjacency alone carries move actions

#### Scenario: Gate descriptions retain the upstream metadata
- **WHEN** a registered grid/wilderness gateway appears
- **THEN** gateway is null or exactly the validated leads_to object from add-local-map-gateway-metadata, and opaque action identity remains authoritative

### Requirement: Wilderness area maps cover a fifteen-cell neighbourhood
Wilderness area_map SHALL cover the 15 by 15 cell neighbourhood centred on the player with visited flags and the current district display name. Its eight legal neighbouring steps SHALL carry the existing canonical movement descriptors; invalid sea, blocked terrain and replaced gateway cells SHALL never become fabricated walkable nodes.

#### Scenario: Neighbourhood is bounded around the current cell
- **WHEN** the player opens area scope in wilderness
- **THEN** the coordinate window is current minus seven through current plus seven in each axis, clipped to valid geography, visits are identified and only legal immediate steps are actionable

### Requirement: Area commission markers distinguish same-map identity from elsewhere
Accepted commission markers SHALL carry a canonical node identity when the destination is on this area map and bearing/distance for destinations elsewhere. Resolving markers SHALL not reveal unvisited room topology.

#### Scenario: Destination points into a fogged dungeon branch
- **WHEN** an accepted commission targets a room beyond the known frontier
- **THEN** the marker may identify its destination but no additional room description, exit graph or geometry is disclosed

#### Scenario: Destination belongs to another map
- **WHEN** a commission resolves outside the displayed area
- **THEN** the payload contains bearing and distance rather than off-map detailed room geometry
