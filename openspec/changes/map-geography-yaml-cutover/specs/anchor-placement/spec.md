# Spec Delta

## MODIFIED Requirements

### Requirement: Every placement's anchor_key resolves against ANCHOR_REGISTRY
Every entry in `ANCHOR_PLACEMENT_REGISTRY` SHALL have an `anchor_key` that exists as a key in the
published geography's composed location views (the map-owned replacement for the former module
registry).

#### Scenario: capital_altoria's placement resolves
- **WHEN** `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]` is inspected
- **THEN** its `anchor_key` (`"capital_altoria"`) exists as a key in the published location views

#### Scenario: No placement references a nonexistent anchor
- **WHEN** every entry in `ANCHOR_PLACEMENT_REGISTRY` is inspected
- **THEN** each entry's `anchor_key` exists in the published location views

### Requirement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial
`ANCHOR_PLACEMENT_REGISTRY` SHALL NOT be required to contain an entry for every published location.
It SHALL contain an entry for exactly those locations that have a grid map built for them, and
SHALL grow one entry per settlement as maps are added.

#### Scenario: The registry follows the built settlement maps
- **WHEN** `ANCHOR_PLACEMENT_REGISTRY` is inspected
- **THEN** it contains one entry per settlement with a built grid map, including
  `"capital_altoria"` and `"village_ciaran"`, and no test asserts that any other published location
  key must also appear

#### Scenario: capital_altoria's placement matches the sample city's spawned AnchorRoom
- **WHEN** `sync_grid()` (the `grid-room-sync` capability) has run and the spawned `AnchorRoom` for
  `capital_altoria` is inspected
- **THEN** `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].zcoord` equals that room's `.xyz[2]` and
  `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].entrance_xy` equals `(room.xyz[0], room.xyz[1])`

#### Scenario: Every placement matches its settlement's spawned AnchorRoom
- **WHEN** `sync_grid()` has run and each registered placement's settlement is inspected
- **THEN** every entry's `zcoord` and `entrance_xy` equal its settlement's sole spawned
  `AnchorRoom` coordinates, and no two entries name the same `zcoord`
