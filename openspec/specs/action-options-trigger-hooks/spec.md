## Purpose

Deterministic trigger call sites for the AI action-option proposal service: room entry, conversation completion, and `ui_sync` reconnect — plus the ingress-maintained session-watcher registry that supplies the service's per-session targets without guessing Evennia account APIs.

## Requirements

### Requirement: Room entry triggers a proposal on deterministic movement success

The room-entry trigger SHALL fire only from the deterministic movement-success boundary shared by every project exit lineage — the end of `after_successful_movement` in `typeclasses/exits.py` — and only for a puppeted player-driven entity: `world.rules.player_control.is_player_driven(traverser)` with a live session (a puppeted `PlayerCharacter`, or a possessed-and-puppeted NPC).

#### Scenario: A successful plain-exit traversal schedules a generation

- **WHEN** a puppeted `PlayerCharacter` successfully traverses a plain `MovementCostMixin` exit (settlement commits)
- **THEN** the proposal service receives exactly one fire-and-forget call with the puppeted actor and the watcher registry's live sessions for that actor, and the traversal's own settlement result is unchanged

#### Scenario: A failed movement schedules nothing

- **WHEN** the movement settlement raises (for example the clock charge fails) and compensation restores the player to the source location
- **THEN** no proposal generation is scheduled from the room-entry trigger

#### Scenario: NPC traversal schedules nothing

- **WHEN** an `NPC` traverses the same exit lineage
- **THEN** the room-entry trigger remains silent because the traverser is not a puppeted player-driven entity

#### Scenario: A possessed NPC traversal schedules a generation
- **WHEN** a possessed, puppeted NPC successfully traverses a plain `MovementCostMixin` exit
- **THEN** the proposal service receives exactly one fire-and-forget call naming the possessed NPC as the actor

#### Scenario: Scheduling is registered through transaction.on_commit
- **WHEN** the room-entry trigger fires after a movement success
- **THEN** it registers its scheduling through `transaction.on_commit`, so the fire-and-forget call
  to the proposal service (with the watchers resolved from `watchers_for(actor)`) runs only after the
  movement transaction commits

#### Scenario: A compensated movement never fires the room-entry trigger
- **WHEN** a movement fails or is compensated
- **THEN** the room-entry trigger does not fire

#### Scenario: An unpuppeted player never fires the room-entry trigger
- **WHEN** a player without a puppet moves through the exit lineage
- **THEN** the room-entry trigger does not fire

#### Scenario: A rolled-back outer transaction never fires the room-entry trigger
- **WHEN** the movement's outer transaction rolls back
- **THEN** the room-entry trigger does not fire

#### Scenario: No hook inside world/ai fires the room-entry trigger
- **WHEN** the room-entry trigger's call sites are inspected
- **THEN** no hook inside `world/ai/` fires it

### Requirement: Conversation completion triggers a proposal after publication

The dialogue-reply trigger SHALL fire inside the dispatcher's completion publication path (`_publish_completion` in `web/webclient/actions/dispatcher.py`) only after the reply text, the resulting presentation, and the matching action result are already on the wire, and only for completions whose action ID is `explore.talk_scripted` or `explore.talk_freeform` whose **normalized** result (the outcome actually sent to the client) is `success`.

#### Scenario: A successful scripted-talk reply schedules after publication

- **WHEN** `explore.talk_scripted` completes with outcome `success` and its result and presentation are sent
- **THEN** the service receives exactly one fire-and-forget call carrying the dispatcher's own session and the current coordinator epoch, and that call happens after the reply text, update, and result reach the wire

#### Scenario: A rejected talk never schedules

- **WHEN** a talk action resolves with outcome `rejected` (schedule-blocked NPC, unregistered keyword, no response)
- **THEN** no proposal generation is scheduled from the dialogue trigger

#### Scenario: Non-talk completions never schedule

- **WHEN** any other action (for example `explore.look` or `combat.cast`) completes successfully
- **THEN** the dialogue trigger remains silent

#### Scenario: The trigger carries the dispatcher session and captured epoch
- **WHEN** the dialogue-reply trigger fires
- **THEN** it passes the dispatcher-held session and the coordinator epoch captured at publication,
  so the service publishes through the correct sequence

#### Scenario: Internal errors and retired sequences never schedule
- **WHEN** a completion lands on a rejection path, a stale result, an internal error (including a raw
  `success` that normalizes into an internal error), or a retired sequence
- **THEN** the dialogue trigger does not fire

### Requirement: Reconnect triggers a proposal subject to the stale predicate

The reconnect trigger SHALL fire on the `ui_sync` happy path (`synchronize_session` in `web/webclient/presentation/ingress.py`) after the full snapshot publishes, with the requesting session as the sole watcher. Whether a generation actually starts SHALL be decided by the service's stale predicate (absent options state, changed fingerprint, or a non-ready/non-cached state), never by the hook itself. A session whose options state still matches the current situation SHALL receive no generation.

#### Scenario: A first sync schedules one generation

- **WHEN** a puppeted WebClient sends its first valid `ui_sync` with no prior options state
- **THEN** the snapshot is emitted first and the proposal service is called once with the requesting session as the only watcher

#### Scenario: A sync with a still-current ready state schedules nothing

- **WHEN** a session reconnects and its options state is `ready` for the current fingerprint
- **THEN** no generation is scheduled and the render continues to assemble from stored state

#### Scenario: A sync during degraded-but-cached state schedules nothing

- **WHEN** a session's options state is `degraded` and the current fingerprint is cached
- **THEN** the stale predicate suppresses a new generation

### Requirement: The watcher registry is ingress-maintained and pruned

`web/webclient/presentation/watchers.py` SHALL expose `watchers_for(actor)` returning the live `(session, coordinator_epoch)` pairs currently watching that actor, and SHALL be updated only by the WebClient ingress: every successful `synchronize_session` registers its session (covering both `ui_sync` and post-command refresh), and every registration prunes entries whose session is no longer connected.

#### Scenario: Sync and command settlement register the same live session

- **WHEN** a puppeted session synchronizes through `ui_sync` and later through a post-command refresh
- **THEN** `watchers_for(actor)` returns exactly the live WebClient sessions for that actor, each with the coordinator epoch current at registration time

#### Scenario: A disconnected session is pruned on the next registration

- **WHEN** a session's transport closes and a different session for the same actor registers
- **THEN** the closed session's watcher entry is removed from the registry, and a push to any stale leftover would be silently dropped by the epoch guard

#### Scenario: Surviving stale entries are harmless
- **WHEN** a stale watcher entry survives a disconnect
- **THEN** it is harmless because the epoch guard in the push seam silently drops retired sequences

### Requirement: Every trigger is fire-and-forget, non-raising, and non-mutating

Every trigger hook SHALL invoke the service without blocking its caller, SHALL swallow and log bounded diagnostics on any synchronous failure of the scheduling call, and SHALL NOT alter the movement settlement result, the action result, the snapshot, or any canonical game state. No module under `world/ai/` SHALL contain or call a trigger.

#### Scenario: A scheduling failure cannot break the move

- **WHEN** the service's scheduling call raises synchronously inside the movement-success path
- **THEN** the traversal still completes exactly as before, the failure is logged with a bounded diagnostic, and no state change occurs

#### Scenario: A rolled-back movement transaction never schedules

- **WHEN** a traversal succeeds inside an outer transaction that subsequently rolls back
- **THEN** the on_commit-registered trigger never fires, so no proposal is derived from a room the player never reached

#### Scenario: Triggers never originate in the generative layer

- **WHEN** the repository contract scan inspects modules under `world/ai/`
- **THEN** none of them reference the trigger call sites or the proposal-service scheduling API

#### Scenario: Schedules issue outside the caller's critical section
- **WHEN** any trigger schedules proposal work
- **THEN** the schedule is issued outside the caller's critical section so arrival, command handling,
  and publication are never delayed by proposal work

#### Scenario: The room-entry schedule waits for commit
- **WHEN** the room-entry trigger schedules
- **THEN** it registers through `transaction.on_commit` so it runs only after the movement
  transaction commits, and a rolled-back outer transaction never fires it

#### Scenario: Dialogue and reconnect schedules wait for publication
- **WHEN** the dialogue or reconnect trigger schedules
- **THEN** it fires only after publication has fully settled