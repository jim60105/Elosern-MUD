# Spec Delta

## MODIFIED Requirements

### Requirement: Map panels use exact layer and precision discriminators
Map panels SHALL retain exact versioned layer schemas and existing precision/disclosure rules; wilderness area schema4 SHALL extend schema3 terrain, display annotations and entities with a bounded district overview while unknown runs remain minimal.

#### Scenario: Coordinate frames are not interchangeable
- **WHEN** a player crosses from settlement to wilderness or enters another interior
- **THEN** the new panel changes stable map/frame identity and its node geometry has the new declared units, without inheriting coordinates from the prior frame

#### Scenario: Malformed or secretly enriched records are rejected
- **WHEN** a node, unlit district, overview run or approximate marker has extra fields or wrong discriminator types
- **THEN** both validators reject it rather than preserving unknown metadata

#### Scenario: Display additions cannot enrich unknowns
- **WHEN** schema4 includes district/terrain/ford labels, settlement flags, landmark names, hostile count/threat and the district overview
- **THEN** fields validate only in their exact disclosed record variants, old wilderness schemas reject, unknown records gain no metadata and existing logical byte limits remain

## ADDED Requirements

### Requirement: District overview records have an exact bounded shape
A wilderness `district` SHALL be `null` or an object with exactly the district key, a display name of at most 128 code points, a ladder kilometre cell size, a coarse window and south-to-north RLE rows; the window SHALL contain the current cell and stay inside the 0..2700 frame.

#### Scenario: A valid overview is accepted
- **WHEN** a lit district body carries a window, merged runs whose lengths sum to the width, and only ladder cell sizes
- **THEN** both validators accept it and expose the same cell coordinates and terrain facts

#### Scenario: Malformed overviews are rejected
- **WHEN** the overview has unknown fields, an unmerged or zero-length run, a wrong row count, a window that misses the current cell or leaves the frame, an off-ladder cell size, a long name, an unknown band or the `sea` terrain class
- **THEN** both validators reject the whole area map without adopting a partial body

#### Scenario: Overview capacity is finite
- **WHEN** the overview exceeds its declared 8,192-cell, 4,096-run or 65,536-byte bound
- **THEN** the server omits the overview with a diagnostic rather than publishing an oversized or truncated section, and the visible window still publishes
