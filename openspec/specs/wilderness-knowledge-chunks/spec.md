# wilderness-knowledge-chunks Specification

## Purpose
Replace schema1 with bounded chunk-addressed wilderness observations. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Wilderness observations are chunk addressed
Map knowledge SHALL store bounded chunk-addressed wilderness observations and offer deterministic full projections and selected-chunk reads without schema1 conversion.

#### Scenario: Bounded query
- **WHEN** a synthetic20000-visit record spans distant chunks
- **THEN** a small query parses only intersecting chunks, exact membership works and full projection order is deterministic

#### Scenario: Corruption and preservation
- **WHEN** schema1 or malformed selected offsets/ticks/radii/edge padding are read, or a room visit is pruned
- **THEN** corruption rejects without overwriting, and successful pruning preserves all wilderness metadata
