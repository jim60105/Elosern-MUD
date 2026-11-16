# Spec Delta

## Purpose

Decide where a newly activated player character starts. Every subrace names one start
settlement. The start room is that settlement's anchor room, found through authored
settlement identity rather than coordinates or object ids.

## ADDED Requirements

### Requirement: Every subrace declares exactly one start settlement
The lore layer SHALL declare a start-location registry with exactly one row for each subrace in the subrace registry. A row SHALL name its own subrace key and one start-settlement anchor key, and nothing else: no coordinate, no node id, no object id. Loading the registry SHALL fail when any subrace has no row, when a row names an unknown subrace, when a row's key and its declared subrace differ, or when the anchor key is not a non-empty string.

#### Scenario: Complete coverage loads
- **WHEN** the start-location validator runs against a synthetic subrace registry and a start registry with one well-formed row per subrace
- **THEN** it accepts the registry

#### Scenario: A subrace without a row is rejected at load
- **WHEN** the validator runs against a synthetic subrace registry with a subrace that has no start row
- **THEN** it raises an error that names that subrace

#### Scenario: A row for an unknown subrace is rejected at load
- **WHEN** the validator runs against a start registry with a row whose subrace is not in the synthetic subrace registry
- **THEN** it raises an error that names the row

#### Scenario: A malformed row is rejected at load
- **WHEN** a row's key differs from its declared subrace, or its anchor key is empty or not a string
- **THEN** the validator raises an error that names the row

### Requirement: Start settlements resolve before map-world adoption
The static-reference closure SHALL treat the start-location registry as one more declaration family. A candidate map world SHALL be rejected before any persistent write when a start row's anchor has no settlement placement in that candidate, or when the placement's node does not resolve against the candidate's own bindings.

#### Scenario: A start anchor without a placement rejects adoption
- **WHEN** a candidate static world holds a start row whose anchor key has no anchor placement
- **THEN** the closure reports a problem that names the subrace and the anchor, and validating that world raises

#### Scenario: A resolving start anchor adds no problem
- **WHEN** every start row's anchor has a placement whose node resolves in the candidate
- **THEN** the start-location family contributes no problem

#### Scenario: The start family is part of the checked declaration set
- **WHEN** a start row's anchor key changes between two otherwise identical static worlds
- **THEN** the two static worlds have different fingerprints

### Requirement: A subrace's start room is its settlement's anchor room
Resolving a subrace's start room SHALL go from the start row, to that anchor's settlement placement, to the placement node's current coordinate, to the materialized grid room at that coordinate. Resolution SHALL raise a start-location error, and never fall back to another room, when the subrace has no row, the anchor has no placement, the node does not resolve, or no grid room exists at the coordinate.

#### Scenario: Resolution returns the anchor room of the start settlement
- **WHEN** a synthetic subrace's start row names an anchor whose placement node is materialized as a grid room
- **THEN** resolution returns exactly that grid room

#### Scenario: A moved node moves the start room
- **WHEN** the start settlement's anchor node is published at a different coordinate and materialized there
- **THEN** resolution returns the room at the new coordinate without any change to the start row

#### Scenario: Each unresolvable step raises
- **WHEN** resolution runs for a subrace with no row, an anchor with no placement, or a placement node with no materialized room
- **THEN** it raises a start-location error and returns no room
