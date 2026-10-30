# wilderness-elevation-authoring Specification

## Purpose
Validate ordered elevation shapes before authored-map publication. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Elevation shapes reject invalid candidates
The map core SHALL validate optional ordered elevation shapes before candidate publication and preserve valid declarations through serialization.

#### Scenario: Ordered round trip
- **WHEN** a synthetic continent contains overlapping circle/polygon operations or omits the list
- **THEN** valid fields and order survive parse/save and omission stays omitted

#### Scenario: Atomic rejection
- **WHEN** geometry is outside frame, degenerate or self-crossing, or operation fields are invalid
- **THEN** the candidate rejects without changing the prior valid document
