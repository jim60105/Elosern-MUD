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

#### Scenario: One record yields a working location
- **WHEN** a hosted service record targets a valid map-owned room
- **THEN** map synchronization supplies that room/connections and the service owner supplies its host/components/goods without duplicate geometry declarations

#### Scenario: A host-less record yields a room and no NPC
- **WHEN** a hostless place targets a declared interior
- **THEN** the interior and its map-owned doorways exist without creating a host

#### Scenario: A repeated run leaves a host-less room alone
- **WHEN** a hostless joined room synchronizes twice
- **THEN** the stable room is reused once and neither run creates an NPC

#### Scenario: The room is the deliverable and the host is optional
- **WHEN** an interior has no service record
- **THEN** its complete declared map topology still synchronizes without requiring a host or goods

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

#### Scenario: Adding a place adds an interior with no code change
- **WHEN** a service place joins a newly declared interior document
- **THEN** synchronization supplies its room/doorways from map data without a new bootstrap constant or duplicated place geometry

#### Scenario: A repeated run changes nothing
- **WHEN** a joined interior/service synchronizes twice
- **THEN** no room/doorway/host duplicates and live stock is unchanged

#### Scenario: One unresolvable exterior does not stop the rest
- **WHEN** a valid static endpoint cannot be found among materialized persistent rooms
- **THEN** the existing synchronization warning/skip behavior applies to that dependent interior and other resolvable interiors continue; an absent static target instead fails candidate preflight

#### Scenario: Unresolvable exterior warns names the place and continues
- **WHEN** a validated interior endpoint is temporarily unavailable in persistent realization
- **THEN** synchronization warns with the interior and joined place identity when present, skips that dependent operation and preserves the existing non-throwing behavior

