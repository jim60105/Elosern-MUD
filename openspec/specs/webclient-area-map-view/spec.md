# webclient-area-map-view Specification

## Purpose
Render authoritative area-map fog and movement in metric settlements, coordinate-free room graphs and the local wilderness neighbourhood.

## Requirements

### Requirement: Area rendering uses truthful geometry and server fog
AreaMapView SHALL render only validated area_map facts. Settlements SHALL use metre coordinates under uniform pan/zoom with no compressed mode; coordinate-free instance/interior nodes SHALL retain radial layout. Wilderness SHALL render the provided 15 by 15 neighbourhood and current district. Dot spacing and scale captions SHALL remain scale-true.

#### Scenario: Metric settlement has unequal gaps
- **WHEN** the player views and zooms a settlement with unequal edge lengths
- **THEN** the gap ratios remain proportional and dot/scale text reports the same real distance

#### Scenario: Dungeon fog cannot be bypassed by selection
- **WHEN** a dungeon branch is absent from the payload
- **THEN** no hidden node or road is rendered or exposed in accessible detail text

### Requirement: Area selection offers travel only for an authoritative adjacent exit
Selecting a node SHALL expose its readable state/details and 前往 only when its validated server move descriptor permits current adjacency. Activation SHALL submit existing explore.move using the opaque exit reference and current canonical source, never derive a route from map geometry.

#### Scenario: Adjacent exit is actionable in the real component
- **WHEN** a current-adjacent node has a valid move descriptor and is selected
- **THEN** 前往 is reachable by keyboard and pointer and emits the exact descriptor once

#### Scenario: Remote visited node is inspectable only
- **WHEN** a visited but remote node is selected
- **THEN** its name is readable at 16 px or more and it has no move submission
