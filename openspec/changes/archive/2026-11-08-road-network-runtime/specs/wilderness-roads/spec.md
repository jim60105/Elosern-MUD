# Spec Delta

## Purpose

Adopt the generated road network into the published map world, so that road cells are faster to walk and appear on the disclosed area and travel maps without the runtime computing any road.

## ADDED Requirements

### Requirement: Adoption requires a current road network
Map world adoption SHALL accept a candidate only when the committed road artifact decodes and its source signature matches the candidate's inputs. A rejection SHALL leave the published world unchanged and name the regeneration command.

#### Scenario: Stale artifact
- **WHEN** a candidate's road inputs differ from the artifact's signature
- **THEN** adoption raises the map world error naming the regeneration command and the previous bundle stays published

#### Scenario: Corrupt or missing artifact
- **WHEN** the road artifact is absent or fails decoding
- **THEN** adoption raises the map world error and the previous bundle stays published

#### Scenario: Missing parameter document
- **WHEN** a candidate has no road parameter document
- **THEN** adoption rejects it as not current

#### Scenario: Interior edit keeps the artifact current
- **WHEN** a candidate differs only in an interior document
- **THEN** the road gate accepts it

#### Scenario: Offline producers stay ungated
- **WHEN** an offline producer composes and previews a candidate
- **THEN** it reads the candidate with no road artifact and the bundle publishes no road cell

### Requirement: Road cell lookup reads the published bundle
Road cell lookup SHALL answer from the road network of the currently published bundle, and SHALL report no road cell when that bundle carries no network. It SHALL work without the generation extra.

#### Scenario: Published cells
- **WHEN** a bundle with a synthetic road network is published
- **THEN** its road cells answer true, any other cell answers false, and publishing a bundle with no network makes every cell answer false

#### Scenario: Rollback restores the network
- **WHEN** an adoption's persistent synchronization fails
- **THEN** lookup answers from the restored bundle's network

#### Scenario: Bundle identity
- **WHEN** two bundles differ only in their road network
- **THEN** their identities differ

#### Scenario: Independent runtime
- **WHEN** the read view is imported in a fresh interpreter with NumPy and SciPy blocked
- **THEN** import and lookup complete

### Requirement: Road speed needs road cells at both ends of a step
Wilderness terrain SHALL be the road travel context when both ends of a step are road cells, and the existing slower-region terrain otherwise, in both directions.

#### Scenario: Whole road step
- **WHEN** both ends of a cardinal or diagonal step are road cells
- **THEN** the step's terrain is road and its duration uses the road speed

#### Scenario: Partial step
- **WHEN** only one end of a step is a road cell
- **THEN** the step keeps the slower-region terrain in both directions

#### Scenario: Same cell query
- **WHEN** the terrain of a road cell is queried with itself as both ends
- **THEN** it answers road, and a non-road cell answers its regional terrain

#### Scenario: Planner takes the road at equal distance
- **WHEN** two synthetic cardinal-only routes have equal length and only one runs on road cells
- **THEN** the planner picks the road, and its prediction equals the sequential charge

### Requirement: Map facts publish the road fact within disclosure
Area and travel map cell facts SHALL publish whether a disclosed cell is a road cell, and unrevealed cells SHALL publish nothing about roads.

#### Scenario: Road cells publish true
- **WHEN** a revealed window contains synthetic road cells
- **THEN** those cells publish `road: true` and other terrain cells publish `road: false`

#### Scenario: Unrevealed cells publish nothing
- **WHEN** a road cell is unrevealed
- **THEN** the panel publishes it as unknown with no road field

#### Scenario: A republished network is not read from cache
- **WHEN** a different road network object is published over the same terrain, elevation and footprints
- **THEN** the next panel publishes the new road facts
