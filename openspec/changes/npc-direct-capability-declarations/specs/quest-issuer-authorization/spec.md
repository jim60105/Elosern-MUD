# Spec Delta

## MODIFIED Requirements

### Requirement: Commissioner authority is authorable through the import pipeline
NPC imports and source-host declarations SHALL accept direct quest-issuer configuration without a profession. issuer_key SHALL remain optional: nonempty authored keys use existing grammar and duplicate rejection, absent/empty keys use canonical NPC identity. No component is inferred or authority granted automatically.

#### Scenario: An authored record gains the component with its identity
- **WHEN** an NPC declares quest_issuer with valid issuer_key and binding
- **THEN** exactly that authority is installed

#### Scenario: A merchant can also be a commissioner
- **WHEN** an NPC directly declares merchant and person-bound quest_issuer
- **THEN** both function independently with their own configured bindings

#### Scenario: A roster-created commissioner resolves to its identity form
- **WHEN** its explicit issuer_key is absent/empty
- **THEN** the current npc:#dbid identity is retained

#### Scenario: Two records cannot author the same commission identity
- **WHEN** two direct declarations claim the same nonempty issuer_key
- **THEN** the complete batch rejects before writes

#### Scenario: An imported commissioner survives the startup service sync
- **WHEN** an unmanaged imported commissioner carries a service ID absent from roster
- **THEN** source sync does not claim or delete it

#### Scenario: No existing NPC gains issuing authority
- **WHEN** a source record declares no quest_issuer
- **THEN** sync does not infer or attach it

#### Scenario: The rulebook carries a commissioner blueprint
- **WHEN** commission authority is authored
- **THEN** it uses direct quest_issuer configuration and no profession rulebook remains

#### Scenario: An absent issuer_key is a valid identity, not a missing requirement
- **WHEN** issuer_key is absent or empty on a valid direct declaration
- **THEN** the existing npc:#dbid identity form remains valid

#### Scenario: The roster/import split is explicit and accepted
- **WHEN** either roster or import supplies or omits issuer_key
- **THEN** the same validator preserves its authored-key or canonical identity-form semantics

#### Scenario: Batch uniqueness guards against a shared commission list
- **WHEN** two carriers claim one nonempty authored issuer_key
- **THEN** the complete batch rejects the collision before persistence

#### Scenario: The roster can never claim an imported commissioner's anchor
- **WHEN** an unmanaged imported commissioner has component IDs matching or differing from roster rows
- **THEN** sync does not claim/delete it by those IDs; explicit canonical source ownership controls host lifecycle
