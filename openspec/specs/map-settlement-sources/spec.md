# map-settlement-sources Specification

## Purpose
Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Settlement documents own complete local map declarations
Each discovered settlement document SHALL own its graph and location reference, deriving world geometry from that location's cell, its unique anchor_room position and its location-relative wilderness offset, with no independently authored binding coordinates or absolute wilderness origin.

#### Scenario: Discover another local map
- **WHEN** a supported settlement file is added for an existing geographic location
- **THEN** loading discovers it without Python registration and reverse navigation derives from its location reference alone

#### Scenario: Move a bound node
- **WHEN** a node with entry and art references moves
- **THEN** identity and direction remain unchanged and adapters derive the new binding from that document

#### Scenario: PLACE-LOCATION rigid continental translation
- **WHEN** the referenced location cell changes by `(dx,dy)` while the settlement document remains byte-identical
- **THEN** every node's world position changes by `(1000*dx,1000*dy)` metres, and mask hash cells, obstacle cells, midpoint and gate approach cells change by `(dx,dy)` cells, retaining their stable targets and directions

#### Scenario: PLACE-ANCHOR local-frame authority
- **WHEN** the anchor_room moves from local `(100,200)` to `(130,250)` while another node stays at `(170,280)` and the location remains at `(10,20)`
- **THEN** the anchor remains at world `(10500,20500)`, the other node moves from `(10570,20580)` to `(10540,20530)`, and the wilderness mask and location remain unchanged

#### Scenario: PLACE-OFFSET row convention and point geometry
- **WHEN** a location at `(10,20)` has offset `(-1,2)` and mask rows `###`, `.##`, `###`
- **THEN** the absolute origin is `(9,22)`, its midpoint is `(10,23)`, its north-return approach is `(10,21)` and its west-return approach is `(12,23)`; replacing the mask with a single hash retains point-entry semantics with no obstacle cells

#### Scenario: PLACE-SCHEMA removed duplicate authorities
- **WHEN** a settlement supplies binding, wilderness_entry.origin, a non-integer offset or an offset with unknown keys
- **THEN** schema validation rejects the candidate without coercion or legacy fallback; offset dx/dy accept signed integer cell deltas under the core integer bounds

### Requirement: A one-cell mask may declare a physical footprint
A wilderness entry SHALL accept an optional boolean field that makes a mask with exactly one hash cell a physical footprint: that cell is an obstacle cell, several gates are allowed, and each gate's approach is the neighbouring cell opposite its return direction. Without the field, a one-hash mask SHALL keep point-entry semantics.

#### Scenario: Flagged one-cell mask
- **WHEN** a synthetic settlement at location `(10,20)` has a one-hash mask at offset `(0,0)`, the field set to true, and gates with return directions `e` and `ne`
- **THEN** it loads with no gate-count diagnostic, its obstacle cells are exactly `(10,20)`, and the two approach cells are `(9,20)` and `(9,19)`

#### Scenario: Unflagged mask is unchanged
- **WHEN** the same settlement omits the field or sets it to false
- **THEN** it has no obstacle cell, both approaches are `(10,20)`, and the second gate is diagnosed as exceeding the single point gate

#### Scenario: Field on another mask
- **WHEN** the field is true on a mask with two hash cells
- **THEN** a semantic diagnostic names the settlement, and the geometry equals that of the same mask without the field

#### Scenario: Field type
- **WHEN** the field holds a non-boolean value
- **THEN** schema validation rejects the candidate without coercion
