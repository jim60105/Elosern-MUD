## Purpose

Provide immutable physical geography and demographic authoring contracts for the known continent without coupling declarations to persistent room lifecycle.

## Requirements

### Requirement: The known continent has frozen geographic declarations
Geographic consumers SHALL read immutable continent and location values from the shared map source while non-map demographic declarations retain their existing authority.

#### Scenario: Mainland and reserved sites
- **WHEN** a synthetic irregular mainland with reserved geographic sites is loaded
- **THEN** geometry uses its declared kilometre frame and sites create no settlement, population or knowledge

#### Scenario: Location without a local map
- **WHEN** a known location has no settlement document
- **THEN** its geographic identity remains available without fabricating local content

#### Scenario: Mainland control polygon
- **WHEN** an irregular mainland is loaded from explicitly labelled kilometre vertices
- **THEN** geometry uses its declared closed boundary and independently tested polygon/cell-centre rules; source conversion preserves existing vertices through temporary comparison

#### Scenario: Nine geographic anchors
- **WHEN** discovered locations are loaded and resolved by stable identity
- **THEN** every declared geographic cell remains available without room spawning or knowledge revelation; roster size is authored data rather than a fixed-count assertion

#### Scenario: Six reserved harbor sites
- **WHEN** reserved geographic sites are loaded from the continent document
- **THEN** each uses its declared cell and role without creating a named location, settlement, quest or population; the source owns membership rather than a specification-owned count

### Requirement: Population and territory targets preserve authored settlement scale
The continent SHALL retain approximately 30,000,000 inhabitants on approximately 5,000,000 km², including approximately 300 elves as rounded totals. National territory shares SHALL be area targets separate from terrain and actual control.

#### Scenario: Rounded national targets
- **WHEN** demographics are read
- **THEN** Grandia has 12,000,000 people and 38% / 1,900,000 km²; Altoria 9,000,000 and 27% / 1,350,000 km²; Valhalla 9,000,000 and 25% / 1,250,000 km²; remaining neutral lands approximately 500,000 km² have no inferred population total.

#### Scenario: Large fantasy capitals
- **WHEN** capital population and support are authored
- **THEN** 800,000/600,000/400,000 populations remain, totaling 6% of continent population; regional food/storage/water supply supports them, and Valhalla includes pastoral production/trade rather than hunting alone. Density is concentrated in productive areas, never six inhabitants per cell.

### Requirement: Coordinate frames have explicit physical units
Wilderness cell indices SHALL map to absolute meter centers as (1000X+500,1000Y+500). Settlement positions SHALL use integer meters east/north and a logical z layer. Cross-layer geometry SHALL use an explicit anchor transform without assigning coordinates to coordinate-free interiors.

#### Scenario: Bound local anchors
- **WHEN** Altoria and Ciaran local frames are transformed
- **THEN** world_m = cell_center_m(location cell) + local_m - anchor_room_m for every settlement's
  authored anchor room and the location cell its document names; z is never elevation.

#### Scenario: Single-continent authority
- **WHEN** the enclosing frame is read
- **THEN** it covers 2700 by 2700 one-kilometer logical cells, 0<=X,Y<2700; no planet size or further continent is inferred.
