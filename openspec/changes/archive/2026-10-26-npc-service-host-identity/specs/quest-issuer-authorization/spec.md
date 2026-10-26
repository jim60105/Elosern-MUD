# Spec Delta

## MODIFIED Requirements

### Requirement: Every profession row anchors on a component that carries a service identity
Authored host reuse SHALL use canonical host provenance and SHALL NOT require any first capability or component-level service identity.

#### Scenario: A row anchored on an identity-less component fails the contract
- **WHEN** a host declares narrative dialogue first or no capabilities
- **THEN** host lookup remains valid through canonical provenance

#### Scenario: Every existing row satisfies the invariant
- **WHEN** all shipped host declarations synchronize twice
- **THEN** every canonical identity selects exactly one host independently of capability order

#### Scenario: Without enforcement the failure lands at startup, not authoring
- **WHEN** a duplicate canonical host identity exists
- **THEN** full-batch preflight rejects before mutations

#### Scenario: The invariant is promoted from convention to enforcement
- **WHEN** a source-managed host plan is validated
- **THEN** canonical provenance uniqueness is enforced, with no first-component service-id invariant

### Requirement: The QuestIssuer component mirrors the existing service-host component shape
The quest-issuer capability SHALL retain its service_id, optional issuer_key, binding and anchor fields as deterministic authority/configuration only. Host reuse SHALL depend on canonical host provenance, independently of these fields or declaration order.

#### Scenario: The component is a marker and identity holder only
- **WHEN** a commission mutation is requested
- **THEN** the capability delegates to the deterministic owner and performs no quest/reward writes itself

#### Scenario: A commissioner blueprint survives repeated roster synchronization
- **WHEN** the commissioner is reordered or its service_id changes
- **THEN** the same canonical host dbref is reused without duplicates

#### Scenario: The generic host resolver finds a co-located commissioner
- **WHEN** an implicit command has exactly one local commissioner
- **THEN** it resolves that host; zero or multiple remain implicit-command refusal cases

#### Scenario: A missing service_id would break the roster-sync reuse path
- **WHEN** host identity is resolved for a commissioner
- **THEN** lookup does not read service_id and cannot fail due to its absence

#### Scenario: Mutations delegate to the deterministic core
- **WHEN** a quest, reward or record mutation is requested through a commissioner
- **THEN** the component delegates to its deterministic owner and performs no business writes

#### Scenario: The component resolves through the existing generic resolver
- **WHEN** implicit discovery resolves a commissioner
- **THEN** the existing generic component resolver retains its local zero/one/multiple-host behavior
