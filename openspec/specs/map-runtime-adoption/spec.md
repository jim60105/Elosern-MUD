# map-runtime-adoption Specification

## Purpose
Move all permanent interiors and topology to YAML and finish all-world immutable game publication with authoritative validation. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Runtime adoption publishes one complete validated world
Game adoption SHALL publish a complete immutable map snapshot only after map, authoritative external-reference and required artifact validation, leaving prior registries and persistent state unchanged on rejection.

#### Scenario: Rejected world
- **WHEN** a candidate has an invalid scene/service/quest target or stale required partition
- **THEN** no registry subset or persistent room/exit/reference changes are published

#### Scenario: Reload after coordinate movement
- **WHEN** a referenced occupied node moves and the candidate is adopted and synchronized twice
- **THEN** room/exit identity, occupants, homes, inbound references and knowledge timestamps persist through committed reload without duplicate spawning

### Requirement: Permanent interiors are map-owned independently of services
Permanent room identity, prose, scene references and connections SHALL come solely from interior documents, with service records joining existing stable room IDs.

#### Scenario: Standalone and service interiors
- **WHEN** a non-service interior and an existing service interior are loaded and synchronized twice
- **THEN** both exist once, the existing service room tag/join is retained and only the service record contributes a host

#### Scenario: Special links
- **WHEN** a declared interior-to-interior or exterior entrance is changed
- **THEN** the one owning relationship supplies both endpoint/return meanings without hard-coded bootstrap topology
