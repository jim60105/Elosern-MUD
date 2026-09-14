## ADDED Requirements

### Requirement: Effect audiences select recipients without changing skill faction constraints
Each effect SHALL permit an immutable audience of selected candidates, self, selected allies including selected self, or selected enemies. Unconfigured effects SHALL use the complete validated selection. Relation-based audiences SHALL never add unselected entities. Self-bound effects SHALL validate the actor and bind it once. Invalid or contradictory audience declarations SHALL fail authoring.

#### Scenario: Same mechanism serves an alternate element
- **WHEN** a synthetic alternate-element spell combines enemy damage and ally recovery in a mixed selection
- **THEN** only enemies lose HP and only selected allies/self recover, while unselected bystanders remain unchanged

#### Scenario: Ordinary targeting remains free
- **WHEN** an unconfigured attack targets a companion or an unconfigured heal targets an enemy
- **THEN** the selected target receives the ordinary effect

#### Scenario: Explicit self binding is independent
- **WHEN** the caster is not in the explicit pool but one declared effect is self-bound
- **THEN** the actor receives that effect exactly once after ordinary validation
