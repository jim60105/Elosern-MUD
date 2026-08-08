## MODIFIED Requirements

### Requirement: engage creates one persistent local combat session
`engage <target>` SHALL require a PlayerCharacter, one living hostile target in the same room, and no
active session. It SHALL include every bound companion of the player that is co-located and living in
the session's allied team (`player_ids`). It SHALL persist a JSON-safe CombatSessionRecord containing
deterministic ID, mode, room
dbref, participant dbrefs, fled/knockout identities, elapsed rounds, and optional exam ID. Live objects
or Battlefield instances SHALL NOT be stored.

#### Scenario: Present monster can be engaged
- **WHEN** a player invokes `engage` on a living hostile Monster in the current room
- **THEN** one hostile-mode session is persisted and registered with skip safety

#### Scenario: Co-located living companions join the session's allied team
- **WHEN** a player with co-located living bound companions engages a hostile target
- **THEN** the persisted `player_ids` contains the player and each such companion, and the session
  reconstructs them as the allied team

#### Scenario: Knocked-out companions are excluded from a new engagement
- **WHEN** a player whose bound companion is marked knocked out (HP at the nonlethal floor)
  engages a hostile target
- **THEN** the companion is absent from the session's allied team

#### Scenario: Remote or dead target is rejected
- **WHEN** the named target is in another room or has zero HP
- **THEN** no session or world-time change occurs

#### Scenario: Active session blocks another engagement
- **WHEN** a player already has a valid active session
- **THEN** a second `engage` request is rejected without replacing it

#### Scenario: A session with a knocked-out player settles as defeat
- **WHEN** the player is marked knocked out or at zero HP while companions stand
- **THEN** the session settles elapsed rounds and clears combat state as an ordinary defeat

### Requirement: One preflight-valid player action drives one complete ordinary combat round
During active combat, `cast` SHALL build one player ActionRequest and call side-effect-free
`ActionResolver.preflight()` before any initiative action. A preflight rejection SHALL not run NPC
actions/upkeep or consume a round. After successful preflight, a session action provider SHALL supply the
request once for the player and deterministic behavior-policy requests for every other participant —
monsters and allied companions alike, each at most one per round, with targets selected from the
opposing team. `run_round()` SHALL
remain responsible for initiative, resolution, and upkeep. If an earlier initiative action makes the
preflight-valid request reject at the player's turn, the already-started round SHALL remain consumed.

#### Scenario: Player chooses an action before NPC turns run
- **WHEN** the player submits a valid combat cast
- **THEN** initiative may place any combatant first, but the queued request is returned exactly once and
  every eligible non-player participant receives at most one policy action that round

#### Scenario: Companions receive policy actions like monsters
- **WHEN** a round runs with the player, allied companions, and hostile monsters
- **THEN** each companion and each monster receives at most one deterministic policy request, and
  companion requests target the opposing team

#### Scenario: A knocked-out companion receives no action
- **WHEN** a round runs after a companion was knocked out
- **THEN** the companion is absent from initiative action, receives no policy request, and is not a
  selectable target for the player's shortcuts or the opposing team's targeting

#### Scenario: Invalid cast preserves the round before initiative
- **WHEN** ActionResolver preflight rejects the player action
- **THEN** no NPC acts, round count and world clock remain unchanged, and the player may choose again

#### Scenario: Mid-round invalidation does not roll back prior turns
- **WHEN** preflight succeeds but an earlier initiative action makes the player's target invalid
- **THEN** the player's resolution may reject, prior actions and upkeep remain committed, and the round
  count increases once
