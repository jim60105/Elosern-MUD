# npc-capability-declarations Specification

## Purpose

Direct, explicit per-NPC capability declarations: one immutable schema, one
validator and one assembler, shared by imports, authored place hosts and
generated commission roles, with per-capability person or place binding and no
profession blueprints, expansion or hidden defaults.

## Requirements

### Requirement: NPC capabilities are direct unique declarations
An NPC SHALL declare zero or more explicit unique capability types with complete configuration. Imported records and authored hosts SHALL share the same validation and assembly semantics, with no profession, bundle expansion, overrides or implicit schedule/tier defaults.

#### Scenario: Mixed capabilities are independent
- **WHEN** one NPC declares merchant, reception and person-bound commission capability
- **THEN** each uses its own authored identifiers and binding without primary profession semantics

#### Scenario: Duplicate or unknown type rejects
- **WHEN** a batch declares duplicate capability types, unknown fields/types or subsystem runtime values
- **THEN** the full batch is rejected naming record/type/field before persistence

#### Scenario: No player capabilities
- **WHEN** an import targeted at a player character declares components
- **THEN** the named NPC-only validation rejects it without modifying player creation or titles

### Requirement: Each bound capability authors its own binding and unique room
Each service-bearing capability SHALL explicitly declare person or place binding. Person bindings SHALL reject anchors; place bindings SHALL resolve exactly one room. Ordinary narrative dialogue SHALL NOT require service configuration or automatically expose a service.

#### Scenario: Mixed bindings
- **WHEN** a merchant and commission on one NPC use place and person respectively
- **THEN** the merchant pauses off-anchor while the commission retains existing co-presence and authority gates

#### Scenario: Unresolved or ambiguous room
- **WHEN** a place binding has zero or multiple matching rooms
- **THEN** the full operation including prepared interiors and all earlier rows rolls back

#### Scenario: Narrative dialogue
- **WHEN** an ordinary dialogue component has no explicit service association
- **THEN** it remains ordinary dialogue without service settings or a projected service

### Requirement: Generated commissioners carry complete explicit capability configuration
Generated commission roles SHALL carry validated direct capability configuration with explicit person binding and trusted scoped identifiers. Publication and activation SHALL reject absent or conflicting scope/binding before provisioning; ordinary generated narrative dialogue SHALL remain unbound.

#### Scenario: Complete generated activation
- **WHEN** a valid package commission role is published and activated through its real encounter owner
- **THEN** its exact actor receives the declared person-bound quest-issuer plan through shared deterministic assembly, retaining the existing scoped issuer identity and registration checks

#### Scenario: Missing binding rejects
- **WHEN** a commission role omits its explicit capability binding or conflicts with the existing bound actor
- **THEN** publication or activation rejects atomically, with no partial authority or fallback to an unbound service
