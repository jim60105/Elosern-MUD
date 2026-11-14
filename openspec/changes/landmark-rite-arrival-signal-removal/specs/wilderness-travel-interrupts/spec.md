# Spec Delta

## MODIFIED Requirements

### Requirement: Wilderness steps report stateless committed interrupts
Successful wilderness moves SHALL return unique interrupt flags derived from committed before/after state and optional validated walk context without storing walking state. District lighting SHALL raise no flag.

#### Scenario: Transition/context table
- **WHEN** synthetic snapshots independently add each landmark, source, hostile, threshold, night entry or sleeping member
- **THEN** each documented flag raises only for its positive transition/context and combined flags use stable order

#### Scenario: Identity and absent context
- **WHEN** an existing live registered hostile attaches to a recycled room while a step has no walk context
- **THEN** stable identity avoids false hostile flags, natural flags remain and pace/night flags do not raise

#### Scenario: Future birth is not an interruption
- **WHEN** a visible habitat has no actual living hostile but a recovery is pending
- **THEN** no new-hostile interrupt is raised from that future schedule or habitat guidance

#### Scenario: Landmark step raises no lighting flag
- **WHEN** a step reaches a district landmark
- **THEN** the flags are exactly the landmark-reached flag and the flag vocabulary contains no lighting flag
