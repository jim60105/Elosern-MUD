# Spec Delta

## REMOVED Requirements

### Requirement: One preflight-valid player action drives one complete ordinary combat round
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Use the complete-draft automatic ordinary-round requirements and actor-scoped request contract. No compatibility route or data migration.


### Requirement: One submission inside an active session is one ordinary round, by default and structurally
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Member confirmations edit the draft; only its final valid confirmation submits one ordinary round. No compatibility route or data migration.


## MODIFIED Requirements

### Requirement: A round and its settlement form one atomic persistence unit

The shared submission body SHALL persist the round's action effects (HP/resources/knockouts/quest effects), the updated session metadata (round count, fled/knockout sets), and any terminal settlement (exam outcome, clock advance, session clearing) together with draft consumption, round-revision admission and its durable completion receipt as a single durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Upkeep effects commit inside the same unit
- **WHEN** the upkeep settlement stages damaging-tick HP, defeat entries, or quest effects
- **THEN** those upkeep-settled effects commit inside the same unit: the body forwards the session's `simulated` and companion `nonlethal_keys` policy into resolution for both the `opening="round"` and the `opening="overwhelm"` path, and an upkeep settlement failure rolls back the whole round

#### Scenario: Defeat aftermath commits in the one transaction
- **WHEN** a hostile-defeat terminal outcome settles
- **THEN** the complete defeat aftermath (violator departure, weak buff grant, and the adult phases contributed by later changes) commits in that one transaction together with the `settled_tick` marker and the session-record clearing

#### Scenario: Departure deletions ride on_commit
- **WHEN** the defeat aftermath deletes the departing entities physically
- **THEN** the deletions ride `transaction.on_commit`, so an outer round transaction's rollback discards them too

#### Scenario: Accepted draft survives technical failure
- **WHEN** a technical failure follows a participant, item mirror, session metadata or terminal-settlement write
- **THEN** all durable and touched Evennia cache state returns to pre-round values and the accepted complete draft remains recoverable for retry


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


## ADDED Requirements

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


