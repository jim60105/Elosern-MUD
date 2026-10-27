# map-geometry-model Specification

## Purpose
Extract the sparse graph, coordinate and deterministic terrain calculations into an independent Python core and migrate their game callers. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Geometry is explicit and snapshot scoped
Map calculations SHALL use explicit immutable inputs with declared units and deterministic results independent of game services or prior snapshots.

#### Scenario: Coordinate transforms
- **WHEN** a cell (2,3), local (30,40) and local anchor (10,20) are transformed
- **THEN** the cell centre is (2500,3500) metres and the world point is (2520,3520), with no interior physical coordinate

#### Scenario: Snapshot isolation
- **WHEN** two different terrain definitions are classified in succession
- **THEN** each result uses its own inputs and importing/calculating requires no game modules

### Requirement: Directed sparse routes retain authored geometry
Routing SHALL validate and traverse declared directed edges using physical polyline length with work bounded by graph size rather than coordinate span.

#### Scenario: Direction and length
- **WHEN** a three-node graph contains a bent directed road and million-metre separation
- **THEN** the stored direction remains authored, length uses metres, reverse travel needs its own road and no dense lattice is allocated

#### Scenario: Malformed graph
- **WHEN** duplicate IDs/coordinates, absent endpoints, self-loops, duplicate ordered edges or outgoing directions are supplied
- **THEN** route construction rejects before exposing a runtime graph
