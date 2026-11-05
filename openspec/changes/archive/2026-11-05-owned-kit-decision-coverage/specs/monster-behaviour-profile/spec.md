## ADDED Requirements

### Requirement: Owned support actives bind an effective utility decision
The shipped startup tuning SHALL resolve an effective utility decision mode for every registered variant that owns an active skill without a damage effect, judged by the same damage predicate the legacy decision body applies. The check SHALL report each violating variant and skill, SHALL carry no variant roster, and SHALL NOT prevent an edited legacy rollback tuning from loading.

#### Scenario: Legacy support kit reported
- **WHEN** a synthetic variant owning a self-only support skill without damage resolves a legacy decision mode under a synthetic tuning
- **THEN** the check reports that variant and skill

#### Scenario: Utility support kit accepted
- **WHEN** the same variant receives a validated utility override with explicit intelligence, or binds an archetype whose mode is utility
- **THEN** the check reports nothing for it

#### Scenario: Damage kits keep any mode
- **WHEN** a synthetic variant owns only actives with a damage effect under a legacy decision mode
- **THEN** the check reports nothing for it

#### Scenario: Shipped tuning and rollback
- **WHEN** the check runs over the shipped registries and startup tuning, and the shipped rulebook is reloaded with every mode override removed
- **THEN** the shipped tuning reports nothing, and the rollback tuning loads without error
