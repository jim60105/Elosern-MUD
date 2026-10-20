# Spec Delta

## ADDED Requirements

### Requirement: The graphical grid map is independent of automatic ASCII map display

For representable grid and anchor rooms with fixed canonical inputs, changing only automatic ASCII-map display SHALL leave the complete available version-1 `local_map` payload identical. The graphical map SHALL retain its adjacent-node movement descriptors and existing navigation behavior without consuming ASCII text.

#### Scenario: Disabled text maps produce the same complete graphical payload

- **GIVEN** a representable grid or anchor room with fixed player knowledge, valid visual-range options and at least one traversable adjacent exit
- **WHEN** the production presentation registry renders `local_map` with automatic text-map display enabled and disabled, with all canonical inputs held fixed
- **THEN** both payloads are available and deeply equal, including schema version, layer, current node, title, node identities and coordinates, visibility and anchor flags, edges, legend and movement descriptors
- **AND** at least one adjacent node retains a non-null `move` descriptor identifying its real exit and canonical destination

#### Scenario: Explore look leaves the map widget input intact

- **GIVEN** the browser has an available grid-layer payload in either grid-room type and automatic ASCII output is disabled
- **WHEN** `explore.look` with `{"room": true}` succeeds and the normal presentation refresh builds `local_map` again
- **THEN** the refreshed payload is identical to the immediately preceding payload for the same canonical inputs and remains available to the existing widget
- **AND** player location, clock and knowledge remain unchanged by look and presentation
- **AND** the adjacent-node movement descriptors remain usable under the existing `explore.move` action contract
