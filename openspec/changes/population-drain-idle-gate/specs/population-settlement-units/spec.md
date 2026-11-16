# Spec Delta

## ADDED Requirements

### Requirement: Player input is recorded at command and action ingress
The server SHALL record the time of the last player input when a session sends a non-idle text command and when a session with a puppet sends a WebClient UI action. An idle keepalive, a synchronization request and a UI action from a session without a puppet SHALL NOT be recorded.

#### Scenario: Text command
- **WHEN** a session sends a text command that is not the idle keepalive
- **THEN** the recorded time of the last player input is the time of that command

#### Scenario: UI action with a puppet
- **WHEN** a WebClient session with a puppet sends a UI action
- **THEN** the recorded time of the last player input is the time of that action

#### Scenario: Idle keepalive
- **WHEN** a session sends the idle keepalive and nothing else
- **THEN** no player input is recorded

#### Scenario: Synchronization and unpuppeted action
- **WHEN** a WebClient session sends a synchronization request, or a session without a puppet sends a UI action
- **THEN** no player input is recorded

### Requirement: The periodic drain yields to recent player input
The periodic caller SHALL perform no drain run while the last recorded player input is more recent than the configured idle window. It SHALL drain as usual when no input has been recorded or when the window has passed. A skipped repeat SHALL read no population record and emit no event.

#### Scenario: Recent input
- **WHEN** the periodic caller repeats with the drain enabled, a unit lagging, an idle window of 20 seconds and a player input recorded 2 seconds earlier
- **THEN** no drain run happens and the unit's settled-through tick is unchanged

#### Scenario: Window passed
- **WHEN** the periodic caller repeats with the same world and a player input recorded 20 seconds earlier
- **THEN** exactly one drain run happens

#### Scenario: No input recorded
- **WHEN** the periodic caller repeats with the drain enabled, a unit lagging and no player input recorded
- **THEN** exactly one drain run happens

### Requirement: Catch-up and direct drains ignore the idle window
The synchronous catch-up and a direct drain call SHALL settle a lagging closed set whatever the recorded player input is.

#### Scenario: Catch-up during activity
- **WHEN** a unit is behind the world tick, a player input was recorded just now, and the catch-up is asked for that unit
- **THEN** the unit reports the world tick

#### Scenario: Direct drain during activity
- **WHEN** a unit is behind the world tick, a player input was recorded just now, and the drain operation is called directly
- **THEN** the unit moves forward by one slice
