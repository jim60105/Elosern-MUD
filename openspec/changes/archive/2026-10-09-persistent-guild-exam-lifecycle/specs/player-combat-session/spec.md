## MODIFIED Requirements

### Requirement: Active sessions block movement and define pause, forfeit, and recovery outcomes
A PlayerCharacter with an active combat session SHALL be unable to traverse or otherwise leave the
recorded room. Disconnect SHALL pause the persistent session without world-time advance; reconnect SHALL
resume it. `combat forfeit` SHALL settle accumulated time, record ordinary defeat or exam FAIL, and
clear session/context/skip-safety state. Invalid moved/missing recovery SHALL perform the same
cleanup, with exam recovery settling FAIL.

#### Scenario: Exit traversal is blocked during combat
- **WHEN** a player with an active session attempts a room exit
- **THEN** movement is rejected before location changes and the session remains active

#### Scenario: Disconnect and reconnect resume the same session
- **WHEN** a player disconnects and reconnects with valid participants still in the recorded room
- **THEN** no round or world time elapsed and the same session ID/round count resumes

#### Scenario: Explicit forfeit cleans an exam
- **WHEN** a candidate forfeits an active guild examination
- **THEN** the exam records FAIL, accumulated combat time settles once, the persistent host is restored and retained, and the player may request a later attempt

#### Scenario: Ordinary hostile forfeit retains its consequences
- **WHEN** a player forfeits an ordinary hostile session
- **THEN** ordinary defeat aftermath and one accumulated-time settlement occur, without exam restoration or full-pool healing; only guild_exam mode restores the persistent host's normal outfit, capabilities and both full pools

