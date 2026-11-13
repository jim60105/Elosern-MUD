# Spec Delta

## ADDED Requirements

### Requirement: A one-cell mask may declare a physical footprint
A wilderness entry SHALL accept an optional boolean field that makes a mask with exactly one hash cell a physical footprint: that cell is an obstacle cell, several gates are allowed, and each gate's approach is the neighbouring cell opposite its return direction. Without the field, a one-hash mask SHALL keep point-entry semantics.

#### Scenario: Flagged one-cell mask
- **WHEN** a synthetic settlement at location `(10,20)` has a one-hash mask at offset `(0,0)`, the field set to true, and gates with return directions `e` and `ne`
- **THEN** it loads with no gate-count diagnostic, its obstacle cells are exactly `(10,20)`, and the two approach cells are `(9,20)` and `(9,19)`

#### Scenario: Unflagged mask is unchanged
- **WHEN** the same settlement omits the field or sets it to false
- **THEN** it has no obstacle cell, both approaches are `(10,20)`, and the second gate is diagnosed as exceeding the single point gate

#### Scenario: Field on another mask
- **WHEN** the field is true on a mask with two hash cells
- **THEN** a semantic diagnostic names the settlement, and the geometry equals that of the same mask without the field

#### Scenario: Field type
- **WHEN** the field holds a non-boolean value
- **THEN** schema validation rejects the candidate without coercion
