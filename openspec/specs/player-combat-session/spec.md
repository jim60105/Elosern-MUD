# player-combat-session Specification

## Purpose

Define persistent, deterministic player combat sessions.

## Requirements

### Requirement: engage creates one persistent local combat session
`engage <target>` SHALL require a PlayerCharacter, one living hostile target in the same room, and no
active session. It SHALL persist a JSON-safe CombatSessionRecord containing deterministic ID, mode, room
dbref, participant dbrefs, fled/knockout identities, elapsed rounds, and optional exam ID. Live objects
or Battlefield instances SHALL NOT be stored.

#### Scenario: Present monster can be engaged
- **WHEN** a player invokes `engage` on a living hostile Monster in the current room
- **THEN** one hostile-mode session is persisted and registered with skip safety

#### Scenario: Remote or dead target is rejected
- **WHEN** the named target is in another room or has zero HP
- **THEN** no session or world-time change occurs

#### Scenario: Active session blocks another engagement
- **WHEN** a player already has a valid active session
- **THEN** a second `engage` request is rejected without replacing it

### Requirement: One preflight-valid player action drives one complete ordinary combat round
During active combat, `cast` SHALL build one player ActionRequest and call side-effect-free
`ActionResolver.preflight()` before any initiative action. A preflight rejection SHALL not run NPC
actions/upkeep or consume a round. After successful preflight, a session action provider SHALL supply the
request once for the player and deterministic behavior-policy requests for NPCs. `run_round()` SHALL
remain responsible for initiative, resolution, and upkeep. If an earlier initiative action makes the
preflight-valid request reject at the player's turn, the already-started round SHALL remain consumed.

#### Scenario: Player chooses an action before NPC turns run
- **WHEN** the player submits a valid combat cast
- **THEN** initiative may place any combatant first, but the queued request is returned exactly once and
  every eligible NPC receives at most one policy action that round

#### Scenario: Invalid cast preserves the round before initiative
- **WHEN** ActionResolver preflight rejects the player action
- **THEN** no NPC acts, round count and world clock remain unchanged, and the player may choose again

#### Scenario: Mid-round invalidation does not roll back prior turns
- **WHEN** preflight succeeds but an earlier initiative action makes the player's target invalid
- **THEN** the player's resolution may reject, prior actions and upkeep remain committed, and the round
  count increases once

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful flee, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`, then active session/context state SHALL be
cleared.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the player's ordinary innate flee action succeeds
- **THEN** the session settles elapsed rounds, clears combat state, and leaves no second disengagement path

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player
input. After one player request passes preflight, a decided encounter SHALL call the landed overwhelm
resolver. The selected request SHALL be used for the first simulated player turn; subsequent compressed
player turns SHALL use deterministic `basic_attack` against the lowest-HP living enemy. Every turn SHALL
remain a normal ActionRequest and emit compressed EventLogs; no path SHALL directly assign HP or bypass
quest planners. Undecided encounters SHALL pause for player input between ordinary rounds.

#### Scenario: Overwhelming player resolves a reachable hunt
- **WHEN** engagement classifies the player's team as overwhelming and the player selects a valid first
  action
- **THEN** only then does the encounter resolve through ActionResolver, emit defeat identity for an
  ordinary lethal target, advance quest progress, and settle its rounds

#### Scenario: Engage alone never runs an overwhelming round
- **WHEN** an overwhelming target is engaged but the player has not submitted an action
- **THEN** neither team acts, no EventLog is emitted, and world time and round count remain unchanged

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action

### Requirement: Startup restores valid sessions and terminates invalid references safely
`sync_guild_economy()` SHALL reconstruct valid persisted sessions and skip-safety registration. Missing,
deleted, moved, duplicated, or malformed participants SHALL produce a diagnostic and deterministic
session termination without leaving the player blocked.

#### Scenario: Reload preserves an active battle
- **WHEN** the server reloads with a valid session whose participants remain in its room
- **THEN** the next player combat action resumes the recorded round count and battlefield membership

#### Scenario: Deleted enemy does not strand the player
- **WHEN** startup finds that every recorded enemy dbref is missing
- **THEN** it closes the session with a diagnostic and clears skip-safety state

### Requirement: Active sessions block movement and define pause, forfeit, and recovery outcomes
A PlayerCharacter with an active combat session SHALL be unable to traverse or otherwise leave the
recorded room. Disconnect SHALL pause the persistent session without world-time advance; reconnect SHALL
resume it. `combat forfeit` SHALL settle accumulated time, record ordinary defeat or exam FAIL, delete
any temporary exam opponent, and clear session/context/skip-safety state. Invalid moved/missing recovery
SHALL perform the same cleanup, with exam recovery settling FAIL.

#### Scenario: Exit traversal is blocked during combat
- **WHEN** a player with an active session attempts a room exit
- **THEN** movement is rejected before location changes and the session remains active

#### Scenario: Disconnect and reconnect resume the same session
- **WHEN** a player disconnects and reconnects with valid participants still in the recorded room
- **THEN** no round or world time elapsed and the same session ID/round count resumes

#### Scenario: Explicit forfeit cleans an exam
- **WHEN** a candidate forfeits an active guild examination
- **THEN** the exam records FAIL, accumulated combat time settles once, the temporary opponent is
  deleted, and the player may request a later attempt
