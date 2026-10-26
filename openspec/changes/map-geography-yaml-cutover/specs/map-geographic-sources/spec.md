# Spec Delta

## Purpose

Move continent declarations and all geographic locations to YAML, retaining non-map lore ownership and deterministic game behavior. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Geographic YAML is the sole map-facing authority
Continent and location documents SHALL supply static geographic declarations and map-facing location identity independently of non-map lore and persistent room lifecycle.

#### Scenario: Unbuilt geographic location
- **WHEN** a location has a valid geographic cell but no authored local map
- **THEN** it loads for geography consumers without creating rooms, floors or instances

#### Scenario: Lore composition
- **WHEN** a location is moved or its map-facing attributes change
- **THEN** game geography follows YAML while political affiliation, population and floor-count lore remain with their existing owners

