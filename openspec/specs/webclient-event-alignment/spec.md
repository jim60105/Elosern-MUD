# webclient-event-alignment Specification

## Purpose
Use committed semantic movement events to publish fresh complete presentation at authoritative area and instance boundaries across graphical and text clients.

## Requirements

### Requirement: Committed area and instance transitions replace deltas with fresh alignment
Successful movement across an authoritative area boundary or instance entry exit or replacement SHALL freshly render the complete eager presentation and publish one snapshot instead of that settlement delta. Boundary identity SHALL use committed map/instance identities, independent of display labels and pooled room objects.

#### Scenario: Same label different map
- **WHEN** a successful move enters a different map key with the same display label
- **THEN** the final publication is one fresh complete eager snapshot

#### Scenario: Pooled wilderness room remains one area
- **WHEN** a successful move reuses a TerrainRoom at new coordinates within the same registered wilderness map
- **THEN** it remains incremental and neither object identity nor coordinate change falsely classifies a boundary

#### Scenario: Instance identity replaces equal-looking scene
- **WHEN** the committed actor enters exits or replaces an instance context with equal labels
- **THEN** the current instance identity produces full alignment

#### Scenario: Unknown comparable identity is conservative
- **WHEN** a successful transition cannot establish comparable source/destination area identities
- **THEN** one fresh complete alignment occurs

#### Scenario: Rejected movement is not a checkpoint
- **WHEN** movement is refused or rolls back before committed traversal
- **THEN** the requested action name produces no alignment fact

### Requirement: One serialized settlement has one final publication owner
Graphical actions and WebClient text settlements SHALL classify committed facts and coalesce same-settlement publication candidates before final publication. Multiple qualifying events SHALL produce one fresh final alignment. Later asynchronous changes SHALL remain separately ordered publications.

#### Scenario: Text and graphical paths agree
- **WHEN** the same authoritative boundary is crossed through a graphical action and ordinary text command
- **THEN** both use the same checkpoint classification after commit; Telnet receives no graphical state

#### Scenario: Nested events coalesce
- **WHEN** movement and terminal settlement qualify in one action while dialogue cleanup requests a push
- **THEN** the completion sends one final complete snapshot before its result and no earlier settlement delta

#### Scenario: Deliberately missed invalidation is repaired
- **WHEN** a canonical eager field changes while its candidate is omitted before a later checkpoint
- **THEN** the checkpoint freshly renders and restores that field instead of resending baseline data

#### Scenario: Retired causal group cannot publish
- **WHEN** a Deferred command or action from an old puppet settles after replacement
- **THEN** its captured old-epoch group emits no state or result into the new epoch

#### Scenario: Alignment retains on-demand lifecycle
- **WHEN** a boundary alignment occurs while area_map/world_map were never opened
- **THEN** neither map presenter runs and same-epoch previously complete maps remain separately retained
