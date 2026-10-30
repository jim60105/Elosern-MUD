# Spec Delta

## Purpose

Publish a filtered41-cell RLE window through existing map transport. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

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
