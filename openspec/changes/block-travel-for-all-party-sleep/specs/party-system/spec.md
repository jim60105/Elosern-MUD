# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Any present forced sleeper makes party travel stationary`
- TO: `### Requirement: Any present sleeper makes party travel stationary`

## MODIFIED Requirements

### Requirement: Any present sleeper makes party travel stationary
Any present effective party member in any sleep SHALL block all party travel before effects, time, resources, knowledge or location writes. Ordinary/interior exits, settlement/grid travel, wilderness steps, both cross-layer directions and flight/cost waivers SHALL obey this gate. Possession SHALL grant no carrying, split party or sleeper teleport. Lawful awake local actions SHALL remain available.

#### Scenario: Every exit family
- **WHEN** an awake possessed companion tries each exit family with a voluntary or forced sleeping owner or other effective companion present
- **THEN** every attempt refuses with the stable sleeping-party reason and unchanged source locations, tick, resources, reserves and knowledge

#### Scenario: Local play
- **WHEN** an awake member interacts or fights locally while a companion is asleep
- **THEN** ordinary lawful local actions remain available; no sleeping body is relocated

#### Scenario: Waiver cannot bypass sleep
- **WHEN** the traverser owns a lawful flight or other movement-cost waiver while a source-present member sleeps
- **THEN** the sleep refusal occurs before waiver pricing and before any destination-room creation or relocation

#### Scenario: Ordinary connectors and both gate directions
- **WHEN** travel uses a non-distance interior connector, settlement/grid edge, wilderness step, grid-to-wilderness gate or wilderness-to-grid return
- **THEN** voluntary and forced sleepers each cause the same pre-write refusal through the real traversal consumer

#### Scenario: Exact presence and effective membership
- **WHEN** a remote member sleeps or a stale/corrupt roster reference is encountered while all source-present effective travellers are awake
- **THEN** the remote sleeper grants no artificial travelling membership and existing canonical membership and fail-closed validation apply without global NPC scans

#### Scenario: All awake behavior remains
- **WHEN** every source-present effective traveller is awake and all other travel gates pass
- **THEN** existing distance integration, fatigue thresholds, waivers and single-charge following remain unchanged

#### Scenario: Reserve cannot erase posture
- **WHEN** a voluntary sleeper has full reserve and route prediction is requested
- **THEN** prediction refuses sleeping travel without reconstructing an awake state or writing anything
