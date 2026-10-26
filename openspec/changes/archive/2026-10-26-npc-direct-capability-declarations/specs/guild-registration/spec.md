# Spec Delta

## MODIFIED Requirements

### Requirement: Service hosts are created and converged from a declarative YAML roster
The service roster SHALL derive from each hosted place's canonical identity, spawn room and direct capability declarations. Complete catalog and unique anchor validation SHALL precede atomic assembly. Reused hosts SHALL preserve location and subsystem state under canonical provenance ownership.

#### Scenario: Shipped roster recreates today's two hosts bit-for-bit
- **WHEN** the current declared roster is rebuilt
- **THEN** each host matches its current authored name/profile/age and explicit components without historical roster-count assumptions

#### Scenario: Config-time roster validation rejects a nameable offense without DB access
- **WHEN** a direct component is unknown or missing configuration
- **THEN** catalog loading rejects the complete candidate with named errors

#### Scenario: An unresolvable anchor room fails sync closed and names the row
- **WHEN** an anchor has zero/multiple/non-Room matches
- **THEN** the complete operation rolls back, including prepared interiors

#### Scenario: Assembly is the shared helper, not a code-side literal
- **WHEN** imports and service hosts assemble declarations
- **THEN** both use the same validated capability plan, with no second attach loop

#### Scenario: Idempotent re-sync changes nothing
- **WHEN** the same source synchronizes twice
- **THEN** no host duplicates, runtime state resets or extra capability slots occur

#### Scenario: A host is declared exactly once
- **WHEN** host source definitions are enumerated
- **THEN** each appears only on its canonical place, without a separate hand-authored roster

#### Scenario: The derived roster reproduces the pre-change hosts
- **WHEN** shipped definitions are converted
- **THEN** each preserves its component functionality without profession fields

#### Scenario: Config-time batch validation covers every named offense
- **WHEN** required fields, duplicate types, refs or bindings are malformed
- **THEN** nothing is cached or persisted from the rejected candidate

#### Scenario: Sync resolves rows and reuses hosts under the unchanged contract
- **WHEN** a declaration is synchronized
- **THEN** host_key uses unique canonical profile provenance and reused identity/location/state remain unchanged
