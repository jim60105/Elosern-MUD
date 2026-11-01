# Spec Delta

## MODIFIED Requirements

### Requirement: The continent remains virtual with bounded local lookup
The wilderness SHALL comprise 2700 by 2700 one-kilometer logical cells with east/north axes and authoritative coastline/terrain validity, rejecting complete physical ridge walls and water through bounded local lookup without whole-frame scans or room materialization.

#### Scenario: Frame and sea margin
- **WHEN** (-1,0), (2700,0), and ocean-margin (0,0) are queried
- **THEN** all are invalid for foot movement; ordinary land cells remain valid subject to local obstacles and footprints, and the frame is never pre-created as rooms

#### Scenario: Anchor and port land
- **WHEN** all declared anchor centres and harbour centres are evaluated
- **THEN** all remain inside the mainland polygon while knowledge visibility remains authoritative and unbuilt anchors create no invented settlement maps

#### Scenario: The closed ridge and waterways are impassable
- **WHEN** a shipped stem wall, either arm wall, the crotch, ordinary forest between arms, a river cell and a declared ford are queried
- **THEN** all wall and river cells are refused, forest and ford cells remain walkable subject to footprints, and no mountain-pass exemption exists

#### Scenario: Local work includes branches
- **WHEN** a single coordinate on a synthetic branch is queried
- **THEN** validity uses snapshot-local row geometry and existing local terrain masks without scanning the frame, allocating a ridge raster or materializing rooms
