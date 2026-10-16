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

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful party retreat, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`. Then active session/context state SHALL
be cleared. The settlement SHALL be idempotent: a
terminal outcome SHALL record a durable settled marker so a restart that re-reads the session can
never settle the same rounds a second time.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the confirmed party retreat succeeds
- **THEN** the session settles one added retreat round plus prior elapsed rounds, clears the whole party combat state, and leaves no allied personal disengagement bypass

#### Scenario: A restarted terminal session is not settled twice
- **WHEN** a hostile session reached a terminal outcome and the process terminates before session clearing completes
- **THEN** after restart the session's accumulated time is settled exactly once, not again by session restoration

#### Scenario: Companion gauges regenerate from combat settlement
- **WHEN** a session with a wounded or knocked-out companion reaches a terminal outcome
- **THEN** the companion's HP/MP/SP are regenerated for the accumulated combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

#### Scenario: Settlement scope is the living non-fled roster
- **WHEN** a terminal settlement runs
- **THEN** the settlement entity scope is every living, non-fled member of the session's battlefield
  roster (player, companions, and any non-defeated foe still present), so all participants receive
  gauge regen for the accumulated combat time

### Requirement: The knocked-out player settles the session as defeat
If the player is in the battlefield's knocked-out set at the round cap or
when the round otherwise ends without a side eliminated, the session SHALL
settle with outcome `defeat` — the defeated player SHALL be settled at HP
1 (the nonlethal floor applied by the defeat aftermath), never left at a
0-HP persisted statue.

#### Scenario: Cap reached with the player knocked out
- **WHEN** the player is in the knocked-out set when ROUND_CAP completes
- **THEN** the session settles with outcome `defeat` and the player's stored HP equals the aftermath floor `1` before the recovery phase advances it

### Requirement: A round and its settlement form one atomic persistence unit

The shared submission body SHALL persist the round's action effects, the updated session metadata (round count, fled/knockout sets, the consumed opening-order policy), and any terminal settlement (exam outcome, clock advance, session clearing) together with draft consumption, round-revision admission and its durable completion receipt as one durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Upkeep effects commit inside the same unit
- **WHEN** the upkeep settlement stages damaging-tick HP, defeat entries, or quest effects
- **THEN** those upkeep-settled effects commit inside the same unit: the body forwards the session's `simulated` and companion `nonlethal_keys` policy into its one ordinary resolution, and an upkeep settlement failure rolls back the whole round

#### Scenario: Defeat aftermath commits in the one transaction
- **WHEN** a hostile-defeat terminal outcome settles
- **THEN** the complete defeat aftermath (violator departure, weak buff grant, and the adult phases contributed by later changes) commits in that one transaction together with the `settled_tick` marker and the session-record clearing

#### Scenario: Departure deletions ride on_commit
- **WHEN** the defeat aftermath deletes the departing entities physically
- **THEN** the deletions ride `transaction.on_commit`, so an outer round transaction's rollback discards them too

#### Scenario: Accepted draft survives technical failure
- **WHEN** a technical failure follows a participant, item mirror, session metadata or terminal-settlement write
- **THEN** all durable and touched Evennia cache state returns to pre-round values and the accepted complete draft remains recoverable for retry

### Requirement: Startup restores valid sessions and terminates invalid references safely
The deterministic startup sequence SHALL reconstruct valid persisted sessions and skip-safety
registration through `restore_persisted_sessions()`. A persisted record that cannot be strictly parsed
SHALL be cleared or quarantined without settling world time or participant effects derived from its
untrusted fields, and SHALL leave the player unblocked for ordinary hostile engagement.

#### Scenario: Reload preserves an active battle
- **WHEN** the server reloads with a valid session whose participants remain in its room
- **THEN** the next player combat action resumes the recorded round count and battlefield membership

#### Scenario: Deleted enemy does not strand the player
- **WHEN** startup finds that every recorded enemy dbref is missing
- **THEN** it closes the session with a diagnostic and clears skip-safety state

#### Scenario: Malformed persisted record is cleared at startup
- **WHEN** `active_combat` holds a value that strict parsing rejects (for example `{"not": "a valid record"}`)
- **THEN** startup clears the durable record and the actor's transient combat context and battlefield
  registration without advancing world time and without settling any participant effects

#### Scenario: Hostile engagement succeeds after malformed-record recovery
- **WHEN** startup cleared a malformed persisted record and the player then engages a valid co-located
  living monster
- **THEN** a fresh hostile session is created and the player can act in it

#### Scenario: A well-formed record with bad participants terminates deterministically
- **WHEN** startup finds missing, deleted, moved, duplicated, or malformed participants in a
  well-formed record
- **THEN** it produces a diagnostic and deterministic session termination without leaving the
  player blocked

### Requirement: Malformed session payloads fail closed without unhandled conversion errors
`read_session` SHALL raise `CombatSessionError` with the `malformed_session` reason for any
`active_combat` payload that fails raw conversion or strict parsing, including `TypeError`/`ValueError`
conversion-shape failures, and SHALL NOT leak an unhandled conversion exception. `is_in_active_session`
SHALL return false, and hostile engagement or forfeit SHALL reject with the normalized
`malformed_session` reason while such a payload remains persisted.

#### Scenario: Non-dict payloads normalize to a malformed-session rejection
- **WHEN** `active_combat` holds a non-dict value whose conversion raises `TypeError` or `ValueError`
  (for example an integer or a string)
- **THEN** `read_session` raises `CombatSessionError` with the `malformed_session` reason and
  `is_in_active_session` returns false

#### Scenario: Engagement and forfeit reject a persisted malformed payload without unhandled exceptions
- **WHEN** the player attempts to engage or forfeit while a malformed payload is still persisted
- **THEN** the operation rejects with the normalized `malformed_session` reason and no unhandled
  `TypeError` or `ValueError` escapes

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

### Requirement: Startup combat restoration advances time only after every deterministic clock source is registered

The deterministic startup sequence SHALL run every deterministic sync that precedes session restoration — `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` — before `restore_persisted_sessions()` may advance the world clock.

#### Scenario: All deterministic syncs precede session restoration, which precedes wilderness sync

- **WHEN** the `at_server_start()` call sequence is observed
- **THEN** `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` all run strictly before `restore_persisted_sessions()`, which runs strictly before `sync_wilderness()`

#### Scenario: A due quest deadline inside a recovery window fails

- **WHEN** a cold start begins with an active quest whose `deadline_tick` falls inside the settlement window of a recovered invalid session
- **THEN** the quest record transitions to `FAILED` with reason `deadline_expired` during restoration, because `quest_deadlines` was already registered

#### Scenario: Restoration keeps its wilderness ordering and admits no bypass

- **WHEN** the startup sequence is composed
- **THEN** it still runs `restore_persisted_sessions()` before `sync_wilderness()` so a defeated
  population monster referenced by a committed session is never deleted or respawned first, and no
  recovery window can bypass an unregistered deterministic callback

#### Scenario: The recovery advance runs the ordinary registered stage set

- **WHEN** a recovered session's recovery advance runs `WorldClock.advance`
- **THEN** it runs the same registered stage set as any ordinary advance (`quest_deadlines`,
  `caravan_arrivals`, `shop_hours`, `npc_schedules`, plus `instance_reclamation` registered by
  `sync_grid`), which is why every deterministic sync precedes restoration

### Requirement: Active sessions block movement and define pause, forfeit, and recovery outcomes
A PlayerCharacter with an active session SHALL be unable to traverse or otherwise leave the
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

### Requirement: Player combat submission accepts one explicit target value
The commander/actor draft submission boundary SHALL accept only a concrete list of live participant objects or one of `all-enemies`, `all-allies`, and `all`. It SHALL reject any other scalar, a duplicate explicit participant, or a participant outside the current reconstructed session before initiative. Player-facing NONE and SELF SHALL require an empty list; the facade SHALL bind that empty SELF input to the actor and leave NONE empty.

#### Scenario: Explicit AREA participants drive one round
- **WHEN** a player submits an AREA skill with two distinct current enemy objects
- **THEN** the facade builds one ActionRequest containing both canonical participants and saves the selected actor entry, resolving one ordinary round only when the complete draft is valid

#### Scenario: Approved shorthand reaches ordinary targeting
- **WHEN** a player submits an AREA skill with `all-enemies`
- **THEN** the facade preserves the shorthand for ActionResolver expansion and every resulting candidate passes ordinary target validation

#### Scenario: Old single-object input is not retained
- **WHEN** a production caller passes one participant object instead of a list
- **THEN** the facade rejects the malformed call before initiative rather than wrapping it through a compatibility branch

#### Scenario: SINGLE and AREA keep their target shapes
- **WHEN** a SINGLE or AREA skill is submitted
- **THEN** SINGLE receives exactly one explicit participant, and AREA receives a nonempty explicit list or one approved shorthand

#### Scenario: The facade retains its orchestration ownership
- **WHEN** a submission is processed
- **THEN** the facade retains battlefield reconstruction, shared preview, `ActionResolver.preflight()`, initiative, session persistence, terminal settlement, and recovery ownership

#### Scenario: The facade never owns compression
- **WHEN** compression dispatch is needed
- **THEN** interactive dispatch never compresses and independent noninteractive overwhelm consumers retain their own boundary

#### Scenario: No single-object compatibility overload exists
- **WHEN** a caller attempts the old single-object call shape
- **THEN** no single-object compatibility overload exists to accept it

### Requirement: Telnet combat discovery and target tokens have rule parity
`combat actions` SHALL list every owned active skill in deterministic handler order and assign session-local target tokens from persisted participant order: `a1`, `a2`, and so on for `player_ids`, then `e1`, `e2`, and so on for `enemy_ids`. A token SHALL remain bound to the same dbref for the session lifetime and SHALL never be persisted separately.

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

#### Scenario: Active-session cast accepts the approved syntax set
- **WHEN** the player casts inside an active session
- **THEN** `cast` accepts one token, a comma-separated list containing tokens only, or one complete approved AREA shorthand, and retains existing one-target display-name search

#### Scenario: Comma input rejects malformed entries before initiative
- **WHEN** comma input contains names, unknown or duplicate tokens, or shorthand/token mixtures
- **THEN** it rejects before initiative

### Requirement: Combat boundaries emit observability events

The complete-draft round submission SHALL emit one `combat_round_settled` info event
through the `world.observability` facade whenever an ordinary round commits,
with `char`, `opponent`, `tick`, `hp_before`, and `hp_after` context, and one
`settlement_done` info event when a terminal settlement commits, with `char`,
`ms`, and notification-count context. Events MUST be emitted after the
round's durable commit and MUST NOT alter the atomic round/settlement unit.

#### Scenario: A committed round leaves one boundary event

- **WHEN** an ordinary combat round commits durably
- **THEN** exactly one `combat_round_settled` event is logged with the
  combatant identities and HP delta in context

#### Scenario: A rolled-back round emits no settlement event

- **WHEN** a round's settlement fails and the whole unit rolls back
- **THEN** no `settlement_done` event is logged for that attempt

#### Scenario: Editing does not pretend a round committed
- **WHEN** a partial draft confirmation or rejected final preflight occurs
- **THEN** no combat_round_settled or settlement_done event is emitted for it

### Requirement: engage_group opens one session against several co-located hostile targets
`world/rules/combat_session.py` SHALL provide `engage_group(actor, targets)`, applying every
validation, companion collection, record construction, battlefield reconstruction, persistence, skip
safety registration, and dialogue-session clearing that single-target engagement performs, with
`enemy_ids` holding one dbref per supplied target in deterministic order.

#### Scenario: A two-enemy session reconstructs, persists, resolves, and settles
- **WHEN** `engage_group()` is called with two living hostile monsters in the actor's room, and the
  player then submits one preflight-valid action
- **THEN** the persisted `enemy_ids` contains both dbrefs, the reconstructed battlefield places both
  on the opposing team, the round resolves, and terminal settlement behaves as it does for a
  single-enemy session

#### Scenario: engage is unchanged for its callers
- **WHEN** `engage(actor, target)` is called
- **THEN** it returns the same shape it returned before this change, persists an `enemy_ids` of
  exactly one dbref, and its call sites require no edit

#### Scenario: One invalid target rejects the whole group
- **WHEN** `engage_group()` is called with one valid monster and one target that is dead, in another
  room, or not a `Monster`
- **THEN** the request is rejected, no session is persisted, no battlefield is registered, and no
  world time changes

#### Scenario: engage delegates to engage_group unchanged
- **WHEN** `engage(actor, target)` is called
- **THEN** it retains its signature and semantics and delegates to `engage_group(actor, [target])`,
  so its existing call sites are unchanged

#### Scenario: Any invalid precondition rejects the whole request
- **WHEN** the actor is not a `PlayerCharacter`, already has an active session, or any supplied
  target is not a living hostile `Monster` in the actor's room
- **THEN** `engage_group()` rejects the whole request — persisting no session

### Requirement: Interactive encounter openings seed a draft and never replace party choices with compression
An encounter-starting selection SHALL seed the initiating actor entry and wait for remaining required actors. Interactive rounds, including overwhelming and solo encounters, SHALL preserve selected commands and SHALL NOT dispatch autonomous compressed basic attacks. Existing encounter-specific opening order SHALL remain explicit and ordinary entry order SHALL NOT change initiative.

#### Scenario: Overwhelming party opening
- **WHEN** an exploration attack opens an encounter with companions under an overwhelming verdict
- **THEN** the initiating choice is saved, no action runs until remaining commands confirm and no compressed automatic attacks replace them

#### Scenario: Opening first actor
- **WHEN** an encounter explicitly grants the initiator first action and that actor has low ordinary initiative
- **THEN** the override applies only to its first complete round; later rounds use normal initiative regardless of command order

#### Scenario: The opening seed takes concrete participants only
- **WHEN** an approved AREA shorthand is handed to the opening seed path
- **THEN** it is rejected before initiative rather than resolved through a compatibility branch, because the initiation already expanded that line-up into the session's concrete enemy identities

#### Scenario: An off-roster participant is rejected before initiative
- **WHEN** the opening seed is handed a participant absent from the reconstructed session's roster
- **THEN** it rejects with the ordinary not-present reason before initiative, exactly as the draft boundary does for the same input, persisting no round

#### Scenario: An opening seed with absent companions runs nothing
- **WHEN** an exploration opening seeds its selection while a required companion has not confirmed
- **THEN** the session and the seed's draft entry are durable together, no action has run, no round time has passed, and later round failures preserve that committed draft

### Requirement: Commander may select only currently controllable allied actors
The authenticated player SHALL remain commander while a chosen eligible party member is the action actor. Authorization SHALL derive from current session and bound party membership and existing ability-to-act rules. Enemy, absent, fled, defeated, knocked-out and action-forbidden members SHALL require no command and SHALL receive no automatic attack.

#### Scenario: Forged actor
- **WHEN** a request names an enemy, another player party member or stale selected actor
- **THEN** the server rejects with a named reason without possession, round advance or state changes

#### Scenario: Actor lifecycle unchanged
- **WHEN** the commander chooses a companion
- **THEN** the account puppet and possession lifecycle remain unchanged

### Requirement: All personal skill choices and costs are actor scoped
Each authorized actor SHALL receive its own complete skill/scale/target/cost choices and disabled reasons through the shared authoritative preview. The server SHALL independently repeat ownership and capability validation. SELF SHALL bind the selected actor, and skill MP/SP SHALL be charged to that actor.

#### Scenario: Companion SELF and capability
- **WHEN** a companion owns a SELF skill the commander lacks
- **THEN** it is offered for that companion, binds that companion and charges only its resources when resolved

#### Scenario: Actor-specific magnitude eligibility
- **WHEN** only one party actor has the required freeform mastery
- **THEN** only that actor receives the eligible scale ladder and forged scale use by another actor rejects

### Requirement: Free inspection and equipment operations do not select round commands
Opening a bag, inspecting choices and existing equipment operations SHALL retain their free cost semantics. Relevant equipment changes SHALL invalidate affected previews and cause draft revalidation. Companion out-of-combat inventory management, item transfer and companion equipment-management UI SHALL remain excluded.

#### Scenario: Free inspection
- **WHEN** a player opens a bag or inspects an actor skill
- **THEN** no round command, dice, resource cost or elapsed combat time is produced

#### Scenario: Equipment invalidation
- **WHEN** equipment changes a selected actor relevant capability
- **THEN** affected previews and draft entries require authoritative revalidation before any complete round executes

### Requirement: Confirmed round selections persist as one editable session draft
Each session SHALL store one JSON-safe next-round draft bound to session identity and round revision, with at most one confirmed closed-kind command per required actor. Entries SHALL contain validated identities and payload values, never live objects. Before completion, an entry SHALL be replaceable without executing it.

#### Scenario: Replace earlier selection
- **WHEN** two allies need commands and the first confirmed actor chooses another skill or item before the second confirms
- **THEN** the new entry replaces its prior entry; no dice, enemy policy, upkeep, resource deduction or time runs

#### Scenario: Stable serialization
- **WHEN** a confirmed skill, item or tactical command is committed and loaded afresh
- **THEN** its actor/action/target/scale data reconstructs from validated identities without persisted live references

### Requirement: Draft completeness is derived again from authoritative membership
Every confirmation and complete-draft preflight SHALL reevaluate required actor membership and all commands. Invalid entries SHALL produce per-member reselection reasons while retaining valid entries. A changed required set SHALL require a fresh explicit confirmation rather than silently executing an old incomplete draft.

#### Scenario: Changed roster
- **WHEN** an ally joins, leaves or becomes unable to act while choices are collected
- **THEN** required progress updates without a round, valid entries remain and missing or invalid choices are reported

#### Scenario: Resources or equipment change
- **WHEN** an earlier selected command is no longer valid when the final member confirms
- **THEN** no initiative or upkeep starts, invalid entries require replacement and unaffected entries remain

### Requirement: Draft editing has a separate stale-write version
Draft edits SHALL carry the current session identity, round_revision and draft_version. An admitted edit SHALL increment draft_version. A stale or concurrent edit SHALL reject without overwriting a newer confirmed entry or affecting another session or round.

#### Scenario: Concurrent replacement
- **WHEN** two requests edit the same old draft version
- **THEN** at most one edit is admitted and the other receives canonical progress without overwrite

### Requirement: Reconnect and restart restore confirmed selection progress without execution
Confirmed entries SHALL survive disconnect and process restart. Reconnection SHALL restore their session/revision/progress and SHALL NOT invent missing commands, activate tactical choices or advance combat. Session termination SHALL clear its active draft.

#### Scenario: Restart unfinished draft
- **WHEN** one of several members has a confirmed command when transport or process restarts
- **THEN** the confirmed entry remains, missing members remain unselected and elapsed rounds/time are unchanged

### Requirement: No eligible actors leaves command collection paused with explicit party exits
When the required actor set is empty, draft collection SHALL remain paused and report no eligible actors. It SHALL NOT execute an empty draft or trigger enemy actions, upkeep or time while querying/editing. Confirmed surrender SHALL remain available, and confirmed retreat SHALL use the ordinary no-acting-ally defeat path.

#### Scenario: All members action forbidden
- **WHEN** transient capability rules leave no member eligible to choose a command
- **THEN** progress shows no-eligible-actors and party exit paths; reconnect or preview does not execute all-empty completeness

### Requirement: Final member confirmation automatically submits one complete ordinary round
The last required valid member confirmation SHALL automatically submit the complete draft without another whole-party confirmation. All commands SHALL preflight against current state before initiative. Initiative SHALL be computed once; each eligible allied selected command SHALL be supplied once and enemies SHALL retain their deterministic policies.

#### Scenario: Complete skill and item draft
- **WHEN** all required allies have valid skill/item commands after the final confirmation
- **THEN** one ordinary round executes in initiative order, with no additional autonomous companion request

#### Scenario: Invalid preflight
- **WHEN** any confirmed entry fails current-state preflight
- **THEN** no actor acts, no enemy decision or upkeep runs and valid draft entries remain available for revision

#### Scenario: One upkeep
- **WHEN** a complete draft resolves successfully
- **THEN** upkeep and round-time accounting run once, execution gates still suppress actors unable to act and the next round starts with no selections

### Requirement: Round revisions execute at most once across retries and stale requests
Admission SHALL serialize on the authoritative session and round revision inside the durable round unit. Duplicate, stale or concurrent final confirmations SHALL NOT resolve effects or settlement twice, including after a terminal session has been cleared or a process restarts.

#### Scenario: Duplicate final request
- **WHEN** the final confirmation is retried before or after restart or terminal cleanup
- **THEN** the same revision has at most one committed round and one time settlement; retries return committed or stale status

#### Scenario: Competing requests
- **WHEN** normal final confirmation races another final confirmation or a confirmed party exit
- **THEN** at most one operation consumes that session revision

### Requirement: Execution-time invalidation loses only the selected action opportunity
A command made invalid by an earlier action SHALL lose its opportunity without retargeting, skill resource deduction or item consumption. The round SHALL NOT pause for replacement. Prior valid actions and normal upkeep SHALL remain committed. Valid misses SHALL retain normal costs.

#### Scenario: Earlier target removed
- **WHEN** an earlier initiative action defeats or removes a later command target
- **THEN** the later actor spends no resource or item, no new target is chosen, earlier effects remain and the round count increases once

#### Scenario: Ordinary miss
- **WHEN** a still-valid skill misses normally
- **THEN** normal skill costs apply and the round remains consumed

### Requirement: Taunt selects one enemy and resolves competing declarations by initiative
Eligible allied Taunt SHALL select one living eligible enemy without a success roll, cost zero MP/SP and consume the selected action. Effects SHALL activate before ordinary actions and expire at round end. For multiple taunters of one enemy, the first in the already-computed initiative sequence SHALL win.

#### Scenario: Entry order has no priority
- **WHEN** two members Taunt one enemy and the slower member confirmed first
- **THEN** the earlier initiative member wins without rerolling initiative; both members consume their actions

#### Scenario: Winner loses eligibility
- **WHEN** the winning taunter becomes knocked out, defeated, absent or fled
- **THEN** later enemy decisions are unrestricted for the remainder of the round and no losing taunter takes over

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

### Requirement: Retreat contests the slowest acting ally against the fastest pursuer
Confirmed retreat SHALL replace all personal commands and attempt before ordinary actions. With pursuers it SHALL use one d100 plus minimum adjusted agility of allies able to act against 51 plus maximum adjusted agility of living present nonfled pursuers, reusing the existing flee constant. Accuracy and Dodge SHALL NOT modify this check.

#### Scenario: Slowest member
- **WHEN** allied adjusted agilities are 10 and 20, pursuer maximum is 15, and d100 is 56
- **THEN** retreat succeeds at 66 >= 66 using the slower ally, independently of accuracy/Dodge

#### Scenario: No pursuers or no acting allies
- **WHEN** no pursuers remain or no allied member can act
- **THEN** no pursuers gives automatic escape without a roll; no acting ally uses ordinary defeat

### Requirement: Successful retreat carries the entire present party and counts one round
A successful retreat SHALL remove the whole present party from combat, carrying knocked-out companions without including them in the agility minimum. Enemies SHALL take no action and exactly one elapsed combat round SHALL be added and settled. The operation SHALL add no healing, revival or invented relocation.

#### Scenario: Carried companion
- **WHEN** an acting ally retreats with a present knocked-out companion
- **THEN** both leave combat, the companion stays knocked out absent existing settlement recovery, no enemy action runs and elapsed time settles once

#### Scenario: Exactly once
- **WHEN** a successful retreat confirmation is duplicated across reconnect or restart
- **THEN** the party outcome and added round/time settle once, never leaving a subset in combat

### Requirement: Failed retreat consumes all allied actions and runs one ordinary enemy upkeep round
A failed retreat SHALL keep the entire party in combat, consume every allied action opportunity, allow eligible enemies their normal initiative actions and run ordinary upkeep once. It SHALL cost no MP/SP, activate no Defend/Dodge/Taunt and execute no old draft command. A nonterminal failure SHALL create a fresh next-round draft.

#### Scenario: No draft or tactical benefit
- **WHEN** a party with pending attacks and tactical declarations confirms a retreat that fails
- **THEN** none of those entries executes or protects anyone; eligible enemy actions and upkeep run once and next-round selections are empty

#### Scenario: Failure rollback
- **WHEN** a technical failure occurs after enemy, upkeep or retreat metadata writes
- **THEN** all round state and caches restore together and the accepted operation remains safe to retry without double time
