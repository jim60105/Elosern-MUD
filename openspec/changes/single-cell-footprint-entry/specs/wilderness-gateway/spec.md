# Spec Delta

## ADDED Requirements

### Requirement: One-cell physical footprints resolve gateways at approach cells
A registered entry declared as a one-cell physical footprint SHALL resolve each gate from that gate's approach cell and return direction, and SHALL NOT resolve any gateway from the footprint cell itself.

#### Scenario: Approach cells
- **WHEN** a synthetic one-cell physical footprint at `(10,20)` has gates with return directions `e` and `w`
- **THEN** the gates' approach cells are `(9,20)` and `(11,20)`, and the entry's footprint cells are exactly `(10,20)`

#### Scenario: Gateway match
- **WHEN** a gateway is looked up at `(9,20)` with direction `e`, at `(9,20)` with direction `n`, and at `(10,20)` with direction `e`
- **THEN** only the first lookup returns the entry and its east-return gate
