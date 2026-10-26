# Spec Delta

## MODIFIED Requirements

### Requirement: One place record yields a complete working location
A service place joined to a declared interior room SHALL synchronize its host/capabilities and goods through existing deterministic owners, while map synchronization independently supplies the room and doorways.

#### Scenario: Joined working service
- **WHEN** a valid hosted place targets a declared room and synchronization runs
- **THEN** one map-owned room/entrance set and declared host/components/goods exist without duplicate spawning

#### Scenario: Hostless and standalone interior
- **WHEN** a hostless place or interior with no service record is synchronized twice
- **THEN** the room exists once and no undeclared host is created

### Requirement: Interiors are created by iterating the place registry
Permanent interiors SHALL be synchronized from interior documents independently of place records, retaining stable room joins, idempotent prose/connection convergence and preflight validation.

#### Scenario: Additional interior
- **WHEN** a supported standalone interior file is added without a service declaration
- **THEN** rooms and connections appear once without a bootstrap constant

#### Scenario: Repeated synchronization
- **WHEN** a service interior is synchronized twice after merchant stock changes
- **THEN** room/doorway/host identities and live stock persist while authored map prose converges

#### Scenario: Missing authored exterior
- **WHEN** an interior relationship targets an absent map node
- **THEN** validation rejects before registry or persistent mutation rather than skipping a broken static world

