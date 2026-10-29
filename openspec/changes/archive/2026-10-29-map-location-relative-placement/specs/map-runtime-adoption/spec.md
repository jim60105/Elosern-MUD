## MODIFIED Requirements

### Requirement: Runtime adoption publishes one complete validated world
Game adoption SHALL publish a complete immutable map snapshot only after shared map, authoritative external-reference and required artifact validation, preserving persistent room and exit identities across location-only movement and leaving prior state unchanged on rejection.

#### Scenario: Rejected world
- **WHEN** a candidate has an invalid scene/service/quest target or stale required partition
- **THEN** no registry subset or persistent room/exit/reference changes are published

#### Scenario: Reload after coordinate movement
- **WHEN** a referenced occupied node moves and the candidate is adopted and synchronized twice
- **THEN** room/exit identity, occupants, homes, inbound references and knowledge timestamps persist through committed reload without duplicate spawning

#### Scenario: ADOPT-LOCATION moved occupied settlement
- **WHEN** only locations.yaml moves a settlement-backed location, its partition is regenerated from that candidate, and the final YAML is adopted and synchronized twice
- **THEN** the occupied anchor room and its exits retain database identity, occupants and homes remain attached, all node world positions and wilderness entrances use the new cell, and no duplicate rooms or exits appear

#### Scenario: ADOPT-POINT marker and wilderness entrance agreement
- **WHEN** a centered point-entry settlement is moved through the final YAML and adopted
- **THEN** the world-map marker and point wilderness entrance both equal the moved location cell and the authored gate still reaches the same qualified room

#### Scenario: ADOPT-NO-STALE-BINDING unrepresentable mismatch
- **WHEN** a final-schema world moves a location or its anchor node and the remaining map rules are satisfied
- **THEN** both core and game use the same derived anchors and no obsolete binding-equality check can reject the movement
