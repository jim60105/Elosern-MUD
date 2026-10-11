# Spec Delta

## MODIFIED Requirements

### Requirement: Authority to issue a private commission is authored, never inferred

Private commission authority SHALL reside exclusively in the registered QuestIssuer component. An authored import declaration or explicitly validated generated package issuer declaration MAY provision it through deterministic rules-owned helpers. Display name, typeclass, other components, location, schedule, dialogue prose, and database identity SHALL never confer authority. Runtime provisioning SHALL grant only the validated commission scope to the exact bound actor, preserve the existing component shape and two-form issuer-key grammar, and complete strict commission registration only after actual authorization. Symbolic planning role references SHALL never resolve as runtime authority.

#### Scenario: Ordinary NPC has no authority
- **WHEN** an NPC without QuestIssuer, including a merchant or scripted host, is resolved or asks to offer a commission
- **THEN** no issuer key or commission authority is granted by its other properties

#### Scenario: Generated issuer receives only declared scope
- **WHEN** activation provisions an explicitly validated issuer role and registers its commission
- **THEN** the exact bound actor receives the declared scope through deterministic helpers and its existing grammar-valid actual key is used for strict registration

#### Scenario: Undeclared commission is refused
- **WHEN** a generated issuer attempts an effect outside its validated commission scope or a forged symbolic role is submitted as runtime authority
- **THEN** authorization rejects it and no quest is accepted or registered

#### Scenario: Provisioning and registration roll back together
- **WHEN** activation fails after provisioning or registration
- **THEN** reload and process-local views expose neither partial authority nor a stale commission

#### Scenario: An ordinary NPC cannot issue a commission
- **WHEN** issuer resolution is attempted for an NPC carrying no `QuestIssuer` component
- **THEN** it resolves to nothing, and no issuer key is produced for that entity

#### Scenario: A merchant without the component is still not a commissioner
- **WHEN** issuer resolution is attempted for an NPC carrying `Merchant` and `ScriptedDialogue` but
  not `QuestIssuer`
- **THEN** it resolves to nothing; carrying other service components confers no issuing authority

#### Scenario: No property short of the component confers authority
- **WHEN** an entity's display name, typeclass, other components, location, schedule, dialogue
  authorship, or mere database identity is examined as a candidate source of commission authority
- **THEN** none of them confers that authority

#### Scenario: A component-less entity resolves to no issuer key
- **WHEN** an entity without the `QuestIssuer` component is asked to resolve an issuer key
- **THEN** it SHALL NOT resolve to any issuer key

