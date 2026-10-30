## MODIFIED Requirements

### Requirement: Each exploration exit resolves to exactly one angled or portal target
Every committed exploration move row SHALL resolve in payload order by map bearing, direction word then portal; a withheld wilderness destination SHALL resolve from its generic direction and opaque exit reference without inferred map identity.

#### Scenario: A wilderness exit takes its map bearing
- **WHEN** the layer is `wilderness`, the current node is at (0, 0), and an exit leads to a node at (1, 1); any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit is an angled target at 45° and the same exit's remote-direction marker on the minimap points the same way

#### Scenario: An irregular city bearing is preserved
- **WHEN** the layer is `grid` and an exit leads to a node at (3, 4) from (0, 0); any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit is an angled target at about 36.9° and is not rounded to a cardinal direction

#### Scenario: The map bearing needs both coordinates and a difference
- **WHEN** the destination is absent from the committed local map, or either node lacks coordinates, or the two coordinates are equal; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the map-bearing rule does not apply and the next rule is tried

#### Scenario: A direction word is the fallback
- **WHEN** an exit label is `northeast` and its destination is absent from the committed local map; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit is an angled target at 45°

#### Scenario: Interior doors are portals
- **WHEN** the layer is `interior` and an exit is labelled 公會大廳 with coordinates present on both nodes; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit is a portal and its coordinates are not used to place it

#### Scenario: Same-coordinate stairs are portals
- **WHEN** an exit labelled up leads to a node with the same coordinates as the current node; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit is a portal pinned to the up position


### Requirement: The aimed destination lights on the minimap and motion respects the motion level
A disclosed aimed destination SHALL highlight its existing minimap node; a withheld destination SHALL produce no fabricated highlight, while effective off motion resolves transitions in the commit frame.

#### Scenario: The aimed node lights on the minimap
- **WHEN** the compass aims an exit whose destination is a committed minimap node; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** that node is highlighted on the minimap and the highlight clears when the aim clears

#### Scenario: Motion off removes the shake
- **WHEN** the effective motion level is `off` and a click has no target; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the pad does not animate and the readout shows a static warn-tone flash


### Requirement: The compass degrades honestly
Without a committed local map, compass degradation SHALL retain its existing disabled fallback; with a valid wilderness map, an enabled opaque directional row SHALL remain usable even when its destination node is withheld.

#### Scenario: No local map
- **WHEN** the local map is not committed and the room has a `north` exit and a named door; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the exit labelled north is an angled target at 0°, the door is a portal, both are disabled, and aiming either shows `地圖資料尚未同步。`

#### Scenario: No exits
- **WHEN** the room has no exits; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the pad renders with no pips and no portal track, a click shakes, and the readout idles at `出口 0 · 在場 M`

#### Scenario: Exploration panel unavailable
- **WHEN** the exploration panel is unavailable; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** no compass is rendered and the dock keeps its degraded root


### Requirement: The dialogue screen's exits list stays independent of the exploration root
The dialogue exits list SHALL remain independent of the exploration router and apply the same destination-disclosure policy; withheld wilderness targets retain generic direction, opaque action and safe disabled reason without target facts.

#### Scenario: The dialogue exits list is populated
- **WHEN** a conversation is open in a room with two exits and the player opens `↦ 移動…`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the list shows both exits and activating an enabled one submits exactly the former `explore.move` payload

#### Scenario: A disabled exit keeps its reason
- **WHEN** the room has a locked exit; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the dialogue exits list shows it disabled with its server-authored reason



#### Scenario: Undisclosed directional target
- **WHEN** a synthetic unvisited wilderness neighbour remains outside reveal
- **THEN** it has no local-map node or identifying exit metadata, while its enabled opaque direction can still submit exit_ref/current_node without a fabricated minimap highlight
