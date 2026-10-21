## Purpose

Provide immutable physical geography and demographic authoring contracts for the known continent without coupling declarations to persistent room lifecycle.

## Requirements

### Requirement: The known continent has frozen geographic declarations
The system SHALL declare one known continent with an irregular mainland, rounded demographics, canonical anchor cells and unnamed reserved harbor sites. Declarations SHALL be immutable and independent of temporary source files and of room lifecycle.

#### Scenario: Mainland control polygon
- **WHEN** the boundary is inspected
- **THEN** it closes the ordered kilometer-boundary vertices below and has shoelace area 5,000,000 km²; raster counts need not equal vector area.

| Vertex | East, km | North, km |
| --- | --- | --- |
| 1 | 450 | 100 |
| 2 | 1850 | 100 |
| 3 | 2400 | 450 |
| 4 | 2600 | 1350 |
| 5 | 1930 | 2250 |
| 6 | 1800 | 2600 |
| 7 | 750 | 2550 |
| 8 | 200 | 2050 |
| 9 | 100 | 1050 |
| 10 | 300 | 350 |

#### Scenario: Nine geographic anchors
- **WHEN** canonical positions are resolved
- **THEN** they equal this table, their cell centers are on land, and placement does not spawn rooms or reveal hidden knowledge.

| Registry key | Canonical name | X | Y | Geographic constraint |
| --- | --- | --- | --- | --- |
| `capital_altoria` | 聖潔王都 | 860 | 1080 | Western river valley and hills; riverfront below northern terraces |
| `capital_grandia` | 輝煌帝都 | 1970 | 1280 | Eastern agricultural plain and major river supply |
| `capital_valhalla` | 咆哮王城 | 780 | 1910 | Northwestern highland forest and tribal routes |
| `village_ciaran` | 暗影谷村 | 1340 | 1220 | Underground settlement on the western flank of the central mountains |
| `village_fionnen` | 翠綠森林村 | 1490 | 1510 | Forest on the eastern mountain flank |
| `village_eolas` | 幽月谷村 | 1410 | 2150 | Hidden northern mountain valley near deep forest |
| `dungeon_eternal_night` | 永夜迷宮 | 900 | 2350 | Northern deep forest under nominal Valhalla jurisdiction |
| `dungeon_dragon_nest` | 龍之巢穴 | 2340 | 1220 | Remote eastern Grandia |
| `dungeon_arcane_ruins` | 魔導遺跡 | 480 | 1160 | Western Altoria hills and ancient/mineral sites |

#### Scenario: Six reserved harbor sites
- **WHEN** functional ports are inspected
- **THEN** all centers lie on land at the following cells; none creates named anchors, cities, quests or population.

| Functional site | X | Y | Intended role |
| --- | --- | --- | --- |
| Kingdom southwestern main port | 301 | 350 | River/sea transfer and foreign trade |
| Kingdom western secondary port | 201 | 700 | Western mining and craft exports |
| Kingdom southern secondary port | 600 | 101 | Southern coastal supply |
| Imperial southeastern main port | 2070 | 241 | Agricultural and magical-goods exports |
| Imperial southeastern secondary port | 2400 | 454 | Eastern coastal collection |
| Imperial southern secondary port | 1700 | 101 | Southern coastal transfer |

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
- **THEN** world_m = cell_center_m + local_m - local_anchor_m; Altoria (3500,2850) binds to (860,1080), Ciaran (220,305) to (1340,1220); z is never elevation.

#### Scenario: Single-continent authority
- **WHEN** the enclosing frame is read
- **THEN** it covers 2700 by 2700 one-kilometer logical cells, 0<=X,Y<2700; no planet size or further continent is inferred.
