# Spec Delta

## Purpose

Filter eager wilderness map facts while preserving opaque directional movement. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

### Requirement: All wilderness map publishers enforce reveal boundaries
Eager wilderness map and exit publications SHALL withhold unknown terrain and visit-gated location facts across every serialized branch while preserving permitted known metadata.

#### Scenario: Forest-night all-payload disclosure
- **WHEN** an unlit synthetic forest observer has radius0 and unvisited neighbours including a hidden entry
- **THEN** local-map, exploration and dialogue outputs contain no unknown cell facts or target identity and later area output obeys the same predicate

### Requirement: Opaque directional controls remain executable
A legal wilderness exit to a withheld destination SHALL remain usable by opaque exit reference and current-node guard without publishing destination facts.

#### Scenario: Unknown direction executes
- **WHEN** the existing compass activates an enabled direction whose destination is null
- **THEN** only exit_ref/current_node submit, no minimap target is fabricated and ordinary transactional movement arrives/observes the actual destination
