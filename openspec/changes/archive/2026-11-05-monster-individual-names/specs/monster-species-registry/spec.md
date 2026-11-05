## ADDED Requirements

### Requirement: Monster display names fit the narrow name slots
Species and variant display names SHALL NOT exceed the shared monster name bound of 5 code points, which is the longest name the presence rail and figure plate render without ellipsis. Registry validation SHALL reject a longer name during load.

#### Scenario: Name at the bound
- **WHEN** a synthetic species and variant declare display names of exactly 5 code points
- **THEN** registry validation accepts them

#### Scenario: Over-long name
- **WHEN** a synthetic species or variant declares a display name of 6 code points
- **THEN** registry validation raises the named registry error
