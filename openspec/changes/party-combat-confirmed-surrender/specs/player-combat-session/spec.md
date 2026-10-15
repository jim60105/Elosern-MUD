# Spec Delta

## MODIFIED Requirements

### Requirement: Active sessions block movement and define pause, forfeit, and recovery outcomes
A PlayerCharacter with an active combat session SHALL be unable to traverse or otherwise leave the
recorded room. Disconnect SHALL pause the persistent session without world-time advance; reconnect SHALL
resume it. Explicit revision-bound party surrender confirmation through `combat forfeit` SHALL settle accumulated time, record ordinary defeat or exam FAIL, and
clear session/context/skip-safety state. Invalid moved/missing recovery SHALL perform the same
cleanup, with exam recovery settling FAIL.

#### Scenario: Exit traversal is blocked during combat
- **WHEN** a player with an active session attempts a room exit
- **THEN** movement is rejected before location changes and the session remains active

#### Scenario: Disconnect and reconnect resume the same session
- **WHEN** a player disconnects and reconnects with valid participants still in the recorded room
- **THEN** no round or world time elapsed and the same session ID/round count resumes

#### Scenario: Explicit forfeit cleans an exam
- **WHEN** a candidate confirms surrender in an active guild examination
- **THEN** the exam records FAIL, accumulated combat time settles once, the persistent host is restored and retained, and the player may request a later attempt

#### Scenario: Ordinary hostile forfeit retains its consequences
- **WHEN** a player confirms surrender in an ordinary hostile session
- **THEN** ordinary defeat aftermath and one accumulated-time settlement occur, without exam restoration or full-pool healing; only guild_exam mode restores the persistent host's normal outfit, capabilities and both full pools

#### Scenario: Unconfirmed aliases cannot mutate
- **WHEN** the player invokes forfeit, surrender or an allied flee route without a current explicit confirmation
- **THEN** only a party-scoped consequence prompt is returned, with no settlement, discarded draft or elapsed time


## ADDED Requirements

### Requirement: Party exit requires a commander session round and operation bound confirmation
Retreat and surrender SHALL be session-level operations available independently of selected member. Both SHALL require explicit confirmation bound to commander, current session, round revision and operation. Cancel SHALL preserve the entire draft and advance no time. Stale, forged, replayed and competing confirmations SHALL NOT affect another session or round.

#### Scenario: Cancel and stale prompt
- **WHEN** a player cancels or later confirms a prompt after its session/round changed
- **THEN** cancel retains every draft entry; stale confirmation rejects without mutation or time

#### Scenario: Public bypass forbidden
- **WHEN** an allied personal flee skill or text alias requests exit
- **THEN** it reaches the same party confirmation boundary and cannot perform individual allied escape


### Requirement: Confirmed surrender enters existing defeat or exam FAIL without an extra round
Confirmed surrender SHALL atomically discard draft selections and enter ordinary hostile-defeat or guild-exam FAIL settlement. It SHALL roll no success check, run no extra enemy attack and add no artificial round. Already accumulated time SHALL settle once. Existing defeat aftermath and exam policy SHALL remain unchanged.

#### Scenario: Hostile surrender
- **WHEN** a hostile session with accumulated rounds confirms surrender
- **THEN** ordinary defeat consequences occur, no new safe exit/healing privilege is granted and only accumulated time settles

#### Scenario: Exam surrender and retry
- **WHEN** an exam surrender commits and its confirmation is retried after restart
- **THEN** FAIL and existing host restoration happen once, with no duplicate time or aftermath

#### Scenario: Technical failure
- **WHEN** surrender settlement fails after durable/cache writes
- **THEN** the draft and all touched durable/cache state restore and a later valid retry may complete


