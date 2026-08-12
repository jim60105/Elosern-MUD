# player-combat-session Specification

## Purpose

Define persistent, deterministic player combat sessions.

## Requirements

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

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful flee, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`, and the settlement entity scope SHALL be
every living, non-fled member of the session's battlefield roster (player, companions, and any
non-defeated foe still present), so all participants receive gauge regen for the accumulated combat
time. Then active session/context state SHALL be cleared. The settlement SHALL be idempotent: a
terminal outcome SHALL record a durable settled marker so a restart that re-reads the session can
never settle the same rounds a second time.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the player's ordinary innate flee action succeeds
- **THEN** the session settles elapsed rounds, clears combat state, and leaves no second disengagement path

#### Scenario: A restarted terminal session is not settled twice
- **WHEN** a hostile session reached a terminal outcome and the process terminates before session clearing completes
- **THEN** after restart the session's accumulated time is settled exactly once, not again by session restoration

#### Scenario: Companion gauges regenerate from combat settlement
- **WHEN** a session with a wounded or knocked-out companion reaches a terminal outcome
- **THEN** the companion's HP/MP/SP are regenerated for the accumulated combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

### Requirement: A round and its settlement form one atomic persistence unit

`submit_player_action` SHALL persist the round's action effects (HP/resources/knockouts/quest effects), the updated session metadata (round count, fled/knockout sets), and any terminal settlement (exam outcome, clock advance, session clearing) as a single durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Terminal settlement failure rolls back the round

- **WHEN** a terminal settlement step raises after round effects were applied
- **THEN** the round effects, session metadata, exam outcome, clock tick, and session clearing all roll back together

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player
input. After one player request passes preflight, a decided encounter SHALL call the landed overwhelm
resolver **only when the player's team is the overwhelming side**. The selected request SHALL be used for
the first simulated player turn; subsequent compressed player turns SHALL use deterministic
`basic_attack` against the lowest-HP living enemy. Every turn SHALL remain a normal ActionRequest and
emit compressed EventLogs; no path SHALL directly assign HP or bypass quest planners. The facade SHALL
pass the selected action's actor key and skill key to the resolver so the compressed log marks the
commanded action with a `commanded_action` entry, matched only among the encounter's first-round
logs; this identity plumbing SHALL affect only the log record, never the round sequence, combat
math, or settlement. A foe-overwhelming
(reverse) verdict is informational only: the session SHALL NOT invoke the compressed resolver for it, and
the encounter SHALL play out one ordinary round per player submission, preserving the player's full
per-round agency (skill choice and flee) so no fight is an unavoidable compressed defeat. Undecided
encounters SHALL pause for player input between ordinary rounds.

#### Scenario: Overwhelming player resolves a reachable hunt
- **WHEN** engagement classifies the player's team as overwhelming and the player selects a valid first
  action
- **THEN** only then does the encounter resolve through ActionResolver, emit defeat identity for an
  ordinary lethal target, advance quest progress, and settle its rounds

#### Scenario: Engage alone never runs an overwhelming round
- **WHEN** an overwhelming target is engaged but the player has not submitted an action
- **THEN** neither team acts, no EventLog is emitted, and world time and round count remain unchanged

#### Scenario: The compressed log marks the player's commanded action
- **WHEN** an overwhelming encounter compresses after the player selects a valid action
- **THEN** the compressed EventLogs contain exactly one `commanded_action` entry, prepended to the
  first first-round log matching the player's key and the selected skill, and the encounter's
  rounds, HP mutations, and settlement are identical to the same encounter resolved without the
  identity plumbing

#### Scenario: Foe-overwhelming encounter plays round-by-round
- **WHEN** engagement classifies the foe team as overwhelming and the player submits a preflight-valid action
- **THEN** exactly one ordinary round resolves, the player may choose a different skill or flee next round,
  and the compressed resolver is never invoked

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action

### Requirement: Overwhelm compression is player-direction only
The session facade SHALL invoke the overwhelm resolver only when `classify_overwhelm` returns the player's team; any other verdict (contested or foe-overwhelming) SHALL NOT trigger compression.

#### Scenario: Foe-overwhelming verdict never dispatches the resolver
- **WHEN** the player submits a preflight-valid action in a session classified as foe-overwhelming
- **THEN** the session runs one ordinary round and never calls the overwhelm resolver, for that round or any later round while the verdict holds

### Requirement: Startup restores valid sessions and terminates invalid references safely
The deterministic startup sequence SHALL reconstruct valid persisted sessions and skip-safety
registration through `restore_persisted_sessions()`. Missing, deleted, moved, duplicated, or malformed
participants SHALL produce a diagnostic and deterministic session termination without leaving the
player blocked.

#### Scenario: Reload preserves an active battle
- **WHEN** the server reloads with a valid session whose participants remain in its room
- **THEN** the next player combat action resumes the recorded round count and battlefield membership

#### Scenario: Deleted enemy does not strand the player
- **WHEN** startup finds that every recorded enemy dbref is missing
- **THEN** it closes the session with a diagnostic and clears skip-safety state

### Requirement: Startup restores combat sessions before wilderness population reconciliation
The deterministic startup sequence SHALL restore persisted combat sessions (or otherwise protect
their recorded participants) before any wilderness population reconciliation can delete or replace a
monster referenced by an active session, so a committed terminal outcome is never converted into a
defeat by the reconciliation.

#### Scenario: Defeated population monster survives until session restore
- **WHEN** a restart follows a terminal round against a wilderness population monster whose session
  was not yet settled
- **THEN** session restoration runs before population reconciliation and settles the committed
  outcome, and the reconciliation does not delete or respawn the recorded participant first

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

### Requirement: Player combat submission accepts one explicit target value
`submit_player_action(actor, skill_key, targets_or_shorthand)` SHALL accept only a concrete list of live participant objects or one of `all-enemies`, `all-allies`, and `all`. It SHALL reject any other scalar, a duplicate explicit participant, or a participant outside the current reconstructed session before initiative. Player-facing NONE and SELF SHALL require an empty list; the facade SHALL bind that empty SELF input to the actor and leave NONE empty. SINGLE SHALL receive exactly one explicit participant, and AREA SHALL receive a nonempty explicit list or one approved shorthand. The facade SHALL retain battlefield reconstruction, shared preview, `ActionResolver.preflight()`, initiative, overwhelm dispatch, session persistence, terminal settlement, and recovery ownership. No single-object compatibility overload SHALL exist.

#### Scenario: Explicit AREA participants drive one round
- **WHEN** a player submits an AREA skill with two distinct current enemy objects
- **THEN** the facade builds one ActionRequest containing both canonical participants and drives the existing one-round or overwhelm path once

#### Scenario: Approved shorthand reaches ordinary targeting
- **WHEN** a player submits an AREA skill with `all-enemies`
- **THEN** the facade preserves the shorthand for ActionResolver expansion and every resulting candidate passes ordinary target validation

#### Scenario: Old single-object input is not retained
- **WHEN** a production caller passes one participant object instead of a list
- **THEN** the facade rejects the malformed call before initiative rather than wrapping it through a compatibility branch

### Requirement: Telnet combat discovery and target tokens have rule parity
`combat actions` SHALL list every owned active skill in deterministic handler order and assign session-local target tokens from persisted participant order: `a1`, `a2`, and so on for `player_ids`, then `e1`, `e2`, and so on for `enemy_ids`. A token SHALL remain bound to the same dbref for the session lifetime and SHALL never be persisted separately. Active-session `cast` SHALL accept one token, a comma-separated list containing tokens only, or one complete approved AREA shorthand; it SHALL retain existing one-target display-name search. Comma input SHALL reject names, unknown or duplicate tokens, and shorthand/token mixtures before initiative.

#### Scenario: Combat actions lists stable tokens and active skills
- **WHEN** a Telnet player requests `combat actions` before and after one nonterminal round
- **THEN** the same participant dbrefs retain the same `aN` and `eN` tokens and active skills retain stored order

#### Scenario: Comma-separated tokens submit AREA targets
- **WHEN** the player enters `cast wind_blade=e1,e2`
- **THEN** both tokens resolve from the active record and the same explicit-list facade used by the WebClient receives those participants

#### Scenario: Single display-name lookup remains available
- **WHEN** the player enters one unambiguous existing target name on the right-hand side
- **THEN** the command resolves that one target through existing search and submits it as a one-element list

#### Scenario: Mixed syntax cannot bypass target rules
- **WHEN** the player enters a duplicate token list, a token mixed with a display name, or `all-enemies,e1`
- **THEN** the command rejects before preview, initiative, round count, or world-time change
