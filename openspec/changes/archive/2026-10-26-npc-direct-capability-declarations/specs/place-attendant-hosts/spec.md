# Spec Delta

## MODIFIED Requirements

### Requirement: A place whose service is conversation has a blueprint to host it
A complete hosted place SHALL declare narrative dialogue directly without needing an attendant profession. Dialogue alone SHALL grant no trading, guild, reception or commission authority.

#### Scenario: An attendant place yields a talk-only host
- **WHEN** a place declares only scripted dialogue
- **THEN** one canonical host answers its configured dialogue and carries no other service capability

#### Scenario: An attendant row authoring a trade kwarg is rejected
- **WHEN** a dialogue component authors a shop kwarg
- **THEN** the whole candidate rejects the unknown per-type field

#### Scenario: An attendant place declares no goods
- **WHEN** a dialogue-only place declares goods without merchant
- **THEN** the complete candidate rejects it

#### Scenario: An attendant row authors exactly the dialogue kwarg
- **WHEN** ordinary narrative dialogue is authored
- **THEN** dialogue_key is required while service association and binding are not inferred

#### Scenario: Trade kwargs on an attendant row hit the dead-kwarg rule
- **WHEN** a narrative component carries branch_key
- **THEN** per-type validation rejects the unrelated field

## REMOVED Requirements

### Requirement: Adding the blueprint changes no shipped host
**Reason**: Attendant blueprints are removed.
**Migration**: Declare exactly the current dialogue component on each place; no implicit personnel or services are added.
