## ADDED Requirements

### Requirement: Transition rulebook rejects unbacked condition vocabulary

Because transition condition contexts provide no worn-item fact, the
sexual-transition rulebook loader SHALL reject any rule using the shared
`equipment_worn` condition at load time with an identifying error, so a
syntactically-valid but never-matching transition rule can never ship.

#### Scenario: Grace condition in the transition rulebook fails loading

- **WHEN** `sexual.yaml` contains a transition rule with an
  `equipment_worn` condition
- **THEN** the transition loader rejects the rulebook before mirroring
