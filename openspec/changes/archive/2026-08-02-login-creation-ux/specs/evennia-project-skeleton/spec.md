## MODIFIED Requirements

### Requirement: Runnable Evennia project skeleton
The project SHALL contain an Evennia game directory (Portal + Server) that starts inside the
container and reaches a state where it accepts player connections, structured so that the
directories design doc §3.2 names (`typeclasses/`, `world/`, `commands/`, `web/`) exist and are
ready for later changes to populate.

#### Scenario: Server starts inside the container
- **WHEN** the container starts and runs `evennia start --log`
- **THEN** both the Portal and Server processes reach a running state, and log output is visible on
  the container's stdout

#### Scenario: Player can connect
- **WHEN** a telnet client connects to port 4000, or a browser opens the webclient on port 4001,
  after the server has started
- **THEN** the connection succeeds and the project's custom connection screen is presented

#### Scenario: Directory layout matches the design
- **WHEN** the game directory is inspected after initialization
- **THEN** `typeclasses/`, `world/`, `commands/`, and `web/` exist at the locations design doc §3.2
  specifies, ready to receive the empty-stub subpackages (`world/lore/`, `world/rules/`,
  `world/quests/`, `world/ai/`, `world/imports/`, `world/art/`) that later changes populate
