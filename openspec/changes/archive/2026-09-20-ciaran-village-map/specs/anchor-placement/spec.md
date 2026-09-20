## MODIFIED Requirements

### Requirement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial
`ANCHOR_PLACEMENT_REGISTRY` SHALL NOT be required to contain an entry for every key in
`ANCHOR_REGISTRY`. It SHALL contain an entry for exactly those anchors that have a grid map built
for them, and SHALL grow one entry per settlement as maps are added. It currently holds two,
keyed `"capital_altoria"` and `"village_ciaran"`.

#### Scenario: The registry has exactly one entry after this change
<!-- Scenario name retained verbatim: a MODIFIED block may not drop or rename an existing
     scenario. The "exactly one" wording is historical, from the change that first populated
     this registry; the assertion below is the current two-entry state. -->
- **WHEN** `ANCHOR_PLACEMENT_REGISTRY` is inspected
- **THEN** it contains one entry per settlement with a built grid map — today exactly two,
  `"capital_altoria"` and `"village_ciaran"` — and no test asserts that any other
  `ANCHOR_REGISTRY` key must also appear

#### Scenario: capital_altoria's placement matches the sample city's spawned AnchorRoom
- **WHEN** `sync_grid()` (the `grid-room-sync` capability) has run and the spawned `AnchorRoom` for
  `capital_altoria` is inspected
- **THEN** `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].zcoord` equals that room's `.xyz[2]` and
  `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].entrance_xy` equals `(room.xyz[0], room.xyz[1])`

#### Scenario: Every placement matches its settlement's spawned AnchorRoom
- **WHEN** `sync_grid()` has run and each registered placement's settlement is inspected
- **THEN** every entry's `zcoord` and `entrance_xy` equal its settlement's sole spawned
  `AnchorRoom` coordinates, and no two entries name the same `zcoord`
