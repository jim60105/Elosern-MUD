# webclient-area-map Specification

## Purpose
Publish an on-demand whole-area map with truthful layer geometry, visited-node fog of war and adjacent-only movement descriptors.

## Requirements

### Requirement: Map view requests publish the requested area without changing gameplay
The registered map.view action SHALL accept an area scope request and publish only the requested area_map panel through existing action/panel registries. Reads SHALL not change location, clock, knowledge, quests or persistent room Attributes, including absent instance origins. Maps SHALL not be automatically rebuilt or pushed on committed movement; an open client requests its active scope again.

#### Scenario: Read request is admitted through the normal dispatcher
- **WHEN** an authenticated puppeted client submits map.view with scope area
- **THEN** the normal admission/ordering path publishes area_map and leaves gameplay state unchanged

#### Scenario: Movement does not push expensive maps
- **WHEN** a move commits or a text-command snapshot refresh occurs without map.view
- **THEN** no area/world map is recomputed or newly pushed; unrelated presentation and text remain functional

#### Scenario: An area request does not autocreate an instance origin
- **WHEN** a mappable instance has no persisted origin_room Attribute and the actor requests area scope with an empty quest log or accepted commissions
- **THEN** persistence still contains no origin_room Attribute after the request, gameplay and room state are unchanged, and unavailable world positioning omits only markers that need that unknown origin while the permitted local room graph remains usable

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

### Requirement: Wilderness area maps cover a revealed forty-one-cell neighbourhood
Wilderness area_map SHALL cover the centred41-by-41 window using permanent ground reveal and exact unknown runs; only legal revealed neighbouring steps carry canonical movement descriptors and invalid/replaced cells never become fabricated walkable nodes.

#### Scenario: Neighbourhood is bounded around the current cell
- **WHEN** the player opens area scope in wilderness
- **THEN** the coordinate window is current minus twenty through current plus twenty in each axis, with out-of-frame cells unknown, actual visits distinguished from reveal, and only legal revealed immediate steps actionable

### Requirement: Area commission markers distinguish same-map identity from elsewhere
Accepted commission markers SHALL carry a canonical node identity when the destination is on this area map and bearing/distance for destinations elsewhere. A uniquely registered ordinary interior or its instance origin SHALL supply its canonical enclosing anchor cell for external bearings. Resolving markers SHALL not reveal unvisited room topology or invent coordinates for coordinate-free rooms.

#### Scenario: Destination points into a fogged dungeon branch
- **WHEN** an accepted commission targets a room beyond the known frontier
- **THEN** the marker may identify its destination but no additional room description, exit graph or geometry is disclosed

#### Scenario: Destination belongs to another map
- **WHEN** a commission resolves outside the displayed area
- **THEN** the payload contains bearing and distance rather than off-map detailed room geometry

#### Scenario: Service interiors keep supported external commission pointers
- **WHEN** an actor in a uniquely registered service interior, or an instance entered from it, requests area scope with accepted off-area ANCHOR, GRID, site and regional-hunt destinations
- **THEN** supported destinations have bearings and distances derived from the canonical enclosing anchor and destination cells under the existing area precision contract, without exposing off-area topology or mutating lore, room Attributes, quests, knowledge or clock

#### Scenario: Unknown enclosing position does not manufacture a bearing
- **WHEN** the displayed coordinate-free area's actor origin is genuinely unlocatable or ambiguously registered
- **THEN** markers requiring an external bearing are omitted and valid same-map identities remain usable without fabricated coordinates
