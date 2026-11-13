# map-geographic-sources Specification

## Purpose
Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Geographic YAML is the sole map-facing authority
Continent and location documents SHALL supply static geographic declarations and map-facing location identity independently of non-map lore and persistent room lifecycle.

#### Scenario: Unbuilt geographic location
- **WHEN** a location has a valid geographic cell but no authored local map
- **THEN** it loads for geography consumers without creating rooms, floors or instances

#### Scenario: Lore composition
- **WHEN** a location is moved or its map-facing attributes change
- **THEN** game geography follows YAML while political affiliation, population and floor-count lore remain with their existing owners

### Requirement: A location accepts an optional spacing exemption reason
A location declaration SHALL accept an optional non-blank spacing exemption reason and SHALL expose it to consumers; an absent reason SHALL stay absent.

#### Scenario: Reason round trip
- **WHEN** a synthetic location declares a reason and another declares none
- **THEN** the first exposes that text, the second exposes no reason, and both documents load

#### Scenario: Blank reason
- **WHEN** a location declares a reason that is empty or only whitespace
- **THEN** schema validation rejects the candidate naming the field
