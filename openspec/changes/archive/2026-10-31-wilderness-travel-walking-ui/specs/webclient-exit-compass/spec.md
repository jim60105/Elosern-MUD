## MODIFIED Requirements

### Requirement: The compass is one keyboard composite
Outside active travel presentation the compass SHALL retain its single application focus stop, arrow aim, Enter/Space movement and repeat handling; entering active travel SHALL instead focus the map application and use its travel input contract.

#### Scenario: Arrows aim without moving
- **WHEN** the compass has focus and the player taps ArrowUp
- **THEN** the aim is 0°, the readout names the snapped exit, and no `ui_action` is emitted

#### Scenario: Two arrows give a diagonal and opposing arrows cancel
- **WHEN** the player holds ArrowUp and ArrowRight, and then also ArrowDown
- **THEN** the aim is 45° and then 90°

#### Scenario: Enter moves once and repeat is ignored
- **WHEN** an enabled exit is aimed and the player holds Enter for less than 400 ms with key repeat firing
- **THEN** exactly one `explore.move` is submitted

#### Scenario: Entering exploration focuses the compass
- **WHEN** the client enters ordinary non-travel exploration mode
- **THEN** the compass holds keyboard focus

#### Scenario: Wilderness travel owns movement focus
- **WHEN** committed wilderness exploration selects the travel layout
- **THEN** the map application receives focus and no hidden compass also consumes arrows, Enter or held-walk input
