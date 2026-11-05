# wilderness-area-map-reveal Specification

## Purpose
Publish a filtered41-cell RLE window through existing map transport. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Wilderness runs disclose only revealed terrain
Wilderness area maps SHALL encode a centred41-cell square as validated RLE, exposing terrain facts only for revealed cells and entities only within live sight.

#### Scenario: Anti-peek across payload
- **WHEN** a synthetic window has unknown, remembered, live and hidden cells
- **THEN** unknown runs have only length/kind, remembered cells contain no entities and hidden identity requires visits

#### Scenario: Remembered cells distinguish visits from reveal
- **WHEN** two synthetic in-window cells share identical revealed terrain and only one has an actual visit record
- **THEN** the visited cell carries its own node entry with visited true, the reveal-only cell carries none, and no terrain or unknown run states a visit

#### Scenario: Rows and edge limits
- **WHEN** rows cross the frame boundary or carry wrong totals, extra unknown metadata or invalid band/tier
- **THEN** Python and JS agree on rejection; valid frame padding remains unknown

### Requirement: Existing maps consume bounded atomic reveal payloads
The existing area-map consumer SHALL decode the new wilderness payload through bounded atomic map delivery while retaining server-authored adjacent actions and other-layer semantics.

#### Scenario: Existing consumer and delivery
- **WHEN** a complete map with a revealed gateway arrives or a chunked transfer remains partial/stale
- **THEN** only complete valid maps adopt, current legal action descriptors still work and no client route is derived

#### Scenario: Capacity and query work
- **WHEN** worst-case bounded runs and synthetic20000-visit history are presented
- **THEN** oversize maps become unavailable and warmed median time is<=50ms with bounded selected-chunk reads

### Requirement: A lit current district publishes a coarse overview
When the party's current wilderness cell belongs to a lit map district, the wilderness `area_map` body SHALL carry a `district` overview record for that district; otherwise `district` SHALL be `null`.

#### Scenario: The lit district is published
- **WHEN** the current cell is owned by a lit district
- **THEN** `district` names the district, its authored display name, its chosen kilometre cell size and an RLE window spanning the district's bounds, while the 41-cell visible window is unchanged

#### Scenario: Unlit districts and open sea publish no overview
- **WHEN** the current cell belongs to an unlit district or to no district
- **THEN** `district` is `null` and no terrain outside the 41-cell visible window is published

#### Scenario: The window covers every owned cell and the party
- **WHEN** a lit district contains boundary cells or the party stands on a boundary cell
- **THEN** the coarse window is derived from exact ownership, contains every cell owned by the district and contains the party's current cell

### Requirement: The overview reveals only the lit district's cells
The district overview SHALL contain terrain facts only for cells owned by the published district; every other in-window coarse cell SHALL be an unknown run carrying no fact, place identity, entity or label.

#### Scenario: Neighbouring owners stay fogged
- **WHEN** the district bounding box also covers another district, sea or an unowned cell
- **THEN** those coarse cells are unknown runs and disclose no terrain

#### Scenario: Hidden anchors keep their cover
- **WHEN** a lit district contains a hidden elven village or dungeon footprint
- **THEN** the overview reports its underlying regional terrain, never a settlement identity, label or place record

#### Scenario: Overview carries no identities or entities
- **WHEN** a lit district's overview is inspected
- **THEN** it carries only terrain, elevation band and passability per revealed run, with no node, entity, label, place or landmark record

### Requirement: The overview is bounded by an adaptive kilometre ladder
The overview cell size SHALL be chosen from a fixed kilometre ladder so the coarse cell count, run count and section byte size stay within declared bounds, preferring the finest rung that fits; the fine window keeps its one-kilometre cells.

#### Scenario: A large district uses a coarser rung
- **WHEN** a region district's bounding box would exceed the overview cell budget at a finer rung
- **THEN** the next coarser ladder rung is chosen and the overview still covers the whole district within the declared bounds

#### Scenario: Every shipped district fits a rung
- **WHEN** every authored district's exact bounds are projected through the ladder
- **THEN** each finds a rung within the declared cell, run and byte limits and produces at least one terrain run, so publishing never degrades to an unavailable map

#### Scenario: The sample is deterministic
- **WHEN** a coarse cell is sampled on an even or odd kilometre rung
- **THEN** it uses the one-kilometre cell at `cell_km // 2` from the coarse origin, and the coarse cell containing the party is terrain when the party's cell belongs to the published district
