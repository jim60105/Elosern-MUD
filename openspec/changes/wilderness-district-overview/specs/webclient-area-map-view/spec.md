# Spec Delta

## MODIFIED Requirements

### Requirement: Area rendering uses truthful geometry and server fog
AreaMapView SHALL render only validated area_map facts. Settlements SHALL use metre coordinates under uniform pan/zoom with no compressed mode; coordinate-free instance/interior nodes SHALL retain radial layout. Wilderness SHALL render the provided 41-cell visible window and, when supplied, the current lit district's coarse overview clipped out of that window. Dot spacing and scale captions SHALL remain scale-true.

#### Scenario: Metric settlement has unequal gaps
- **WHEN** the player views and zooms a settlement with unequal edge lengths
- **THEN** the gap ratios remain proportional and dot/scale text reports the same real distance

#### Scenario: Dungeon fog cannot be bypassed by selection
- **WHEN** a dungeon branch is absent from the payload
- **THEN** no hidden node or road is rendered or exposed in accessible detail text

#### Scenario: District overview extends the wilderness frame
- **WHEN** a lit district overview accompanies the visible window
- **THEN** its coarse terrain draws behind the window, the 41-cell window rectangle is cut out of the overview layer, every unknown coarse cell stays fog, and the overview adds no node, road, label or actionable control

## ADDED Requirements

### Requirement: Explored wilderness uses one sight-based style
In the wilderness area map, cells inside the supplied ground-sight disc SHALL render bright, and every other revealed cell SHALL render in the same explored style whether it was walked before or only revealed by the lit district.

#### Scenario: Walked memory and district reveal match
- **WHEN** one revealed cell carries a past visit and another is only revealed by the lit district, both outside live sight
- **THEN** their terrain rendering is identical and neither is brightened by the visit record

#### Scenario: Live sight stays distinct
- **WHEN** a revealed cell lies inside the supplied disc `dx*dx + dy*dy <= (ground_radius + 0.5)**2`
- **THEN** it renders at the live-sight strength and the sight ring still matches the server radius on diagonals and edges
