# map-editor-geography Specification

## Purpose
Implement complete manual continental geometry, location, district, footprint and binding authoring. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Continental authored inputs have direct and explicit editing controls
The editor SHALL support all continent geometry/classifier, geographic location, district/landmark and settlement footprint/binding fields through single-document commands with labelled coordinate frames.

#### Scenario: Move river point
- **WHEN** a river control point is dragged or entered numerically
- **THEN** release/confirmation saves one command, terrain preview derives from core inputs and dependent partition status becomes stale

#### Scenario: Unbuilt location
- **WHEN** a valid geographic location is created without a local map
- **THEN** it is editable and searchable with explicit absent-local-map state and no fabricated rooms

#### Scenario: Footprint and district controls
- **WHEN** a footprint cell or stable district landmark is edited using keyboard controls
- **THEN** only its owning document changes and references/semantic diagnostics remain visible
