# Spec Delta

## ADDED Requirements

### Requirement: The first completed rite adds one discovery narrative
The first committed rite at a district SHALL add one line naming that district to the rite's completion message and SHALL log one discovery event. A repeated rite, a refused rite and a rolled-back rite SHALL add no such line and log no discovery.

#### Scenario: First and repeated rite
- **WHEN** a rite commits at a district with no earlier completion and then commits again
- **THEN** the first completion message carries one extra line naming the district and one discovery event is logged, and the second has neither

#### Scenario: Refused or rolled-back rite
- **WHEN** a rite is refused, or fails after the advance and rolls back
- **THEN** no discovery event is logged
