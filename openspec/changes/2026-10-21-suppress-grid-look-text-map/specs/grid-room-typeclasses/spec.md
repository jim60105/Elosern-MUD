# Spec Delta

## ADDED Requirements

### Requirement: Grid rooms disable automatic text maps by default without disabling navigation

Grid-layer rooms, including anchor rooms, SHALL default to disabled automatic ASCII minimaps during ordinary room look on every client. The default SHALL apply to new maps using the project grid-room typeclasses without requiring a per-map display option. Explicit developer rendering overrides SHALL retain their existing precedence. Disabling automatic text-map display SHALL NOT change room coordinates, map connectivity, shortest-path results or ordinary path-following movement.

#### Scenario: A loaded grid map inherits the disabled text-map default

- **GIVEN** a loaded connected grid map whose options contain valid visual-range settings and no explicit text-map display override
- **WHEN** a player looks at a plain grid room or an anchor room through ordinary room appearance
- **THEN** no automatic ASCII-map message is emitted to any attached text or browser session
- **AND** the room still reports its original coordinates and ordinary appearance

#### Scenario: A new map requires no display configuration

- **GIVEN** a newly authored loaded map using the existing project grid and anchor room types with no display override
- **WHEN** a player looks at either room type
- **THEN** automatic ASCII-map output is disabled without adding a display entry to that map's options

#### Scenario: Route reporting remains available without movement

- **GIVEN** a synthetic connected map with an independently known two-step route and automatic text-map display disabled
- **WHEN** the player invokes `path <destination>`
- **THEN** the reported route contains those same two directions in order
- **AND** the player's location is unchanged

#### Scenario: Localized and English goto still follow the route

- **GIVEN** the same two-step route with traversable exits and automatic text-map display disabled
- **WHEN** the player invokes `前往 <destination>` or its `goto` alias and the scheduled steps complete
- **THEN** the player reaches the same destination by those exits under the existing movement-cost rules
- **AND** the automatic room appearances along the route emit no ASCII minimap message
