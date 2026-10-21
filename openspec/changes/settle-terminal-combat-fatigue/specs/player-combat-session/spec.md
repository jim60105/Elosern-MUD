# Spec Delta

## MODIFIED Requirements

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful party retreat, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`. Mental intervals SHALL settle once for eligible participants from their recorded activity accounting, with natural wake evaluated only after live combat ends and without reviving established defeated entities. Then active session/context state SHALL
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

### Requirement: No eligible actors leaves command collection paused with explicit party exits
Except for canonical engagement where every present allied participant is forced asleep, when the required actor set is empty, draft collection SHALL remain paused and report no eligible actors. It SHALL NOT execute an empty draft or trigger enemy actions, upkeep or time while querying/editing. Confirmed surrender SHALL remain available, and confirmed retreat SHALL use the ordinary no-acting-ally defeat path.

#### Scenario: All members action forbidden
- **WHEN** transient capability rules other than the all-forced-sleep opening leave no member eligible to choose a command
- **THEN** progress shows no-eligible-actors and party exit paths; reconnect or preview does not execute all-empty completeness

## ADDED Requirements

### Requirement: Terminal mental accounting records actual round-boundary posture intervals
Session accounting SHALL retain initial posture and explicit posture transitions by completed-round boundary. Terminal fatigue SHALL derive awake/sleep durations from those intervals and actual elapsed rounds, consume awake time at 12 units/second and restore sleep at 12. No early simulated collapse or retrospective sleep recovery SHALL occur.

#### Scenario: Ten rounds awake
- **WHEN** a continuously awake survivor starts at 360 reserve units (0.1%) and completes ten rounds
- **THEN** live reserve stays 360; terminal 60-second consumption clamps it to zero and forced sleep starts after commit with no retrospective recovery

#### Scenario: Ten rounds asleep
- **WHEN** an undefeated sleeper starts at 71280 units and completes ten rounds
- **THEN** only terminal settlement adds 720 units (0.2%), reaching 72000 and waking into moderate fatigue

#### Scenario: Explicit interval split
- **WHEN** a synthetic explicit effect changes a member from asleep to awake after four of ten rounds
- **THEN** terminal accounting restores 24 seconds and consumes 36 seconds, a net loss of 144 units rather than crediting the entire fight as sleep

### Requirement: All-forced-sleep engagement enters ordinary zero-round defeat
After canonical engagement validation, every present allied party participant being forced asleep SHALL immediately use the ordinary deterministic terminal defeat writer with zero completed combat rounds. It SHALL run no command collection, enemy round or spectator loop. Exam mode SHALL use its existing FAIL policy; existing aftermath time SHALL remain applicable.

#### Scenario: Opening hostile defeat
- **WHEN** a valid direct engagement opens with every eligible present ally forced asleep
- **THEN** ordinary defeat aftermath and diagnostics run once with rounds_elapsed zero and zero invented combat seconds

#### Scenario: Repeat terminal attempt
- **WHEN** that engagement receipt is retried after reload
- **THEN** no second aftermath, fatigue recovery or combat time settles

#### Scenario: Exam opening
- **WHEN** the same canonical all-forced-sleep condition occurs in an examination
- **THEN** ordinary exam FAIL and host restoration apply, without ordinary hostile aftermath

#### Scenario: Invalid engagement
- **WHEN** a remote or otherwise invalid target is submitted with all allies asleep
- **THEN** validation rejects before any session/defeat/time mutation

### Requirement: Terminal physiology cannot reverse defeat and prompts follow aftermath
Mental recovery SHALL never revive a dead/deleted actor, clear existing defeat or undo aftermath. Undefeated sleepers may wake only at terminal settlement; below-threshold forced sleepers SHALL remain stationary after victory. Handoff SHALL be emitted only after the whole terminal/aftermath transaction commits, using actual survivors.

#### Scenario: Defeated sleeper
- **WHEN** terminal sleep recovery would cross 20% for an actor already established defeated
- **THEN** defeat and ordinary aftermath remain authoritative and no revival or eligible handoff is fabricated

#### Scenario: Stationary victory
- **WHEN** an undefeated forced sleeper remains below 72000 after terminal recovery
- **THEN** it stays asleep and all party travel remains blocked; awake local play remains available

#### Scenario: Late companion removal
- **WHEN** terminal aftermath removes or defeats a previously listed candidate
- **THEN** no prompt includes that candidate and no pre-commit transfer is offered

### Requirement: Terminal fatigue joins the complete idempotent round transaction
Reserve, posture, projected buffs and activity metadata SHALL join the existing terminal marker, clock, traits, session/draft and aftermath transaction and rollback caches. A technical failure SHALL restore the whole unit. Nonterminal disconnect/reconnect SHALL neither settle nor execute a round. Unrelated HP/MP/SP settlement SHALL remain unchanged.

#### Scenario: Fault after reserve projection
- **WHEN** a later terminal write fails after multiple participant reserve and buff updates
- **THEN** tick, every participant, session/activity/draft metadata and all touched Evennia caches match pre-round state; retry settles once

#### Scenario: Existing limits
- **WHEN** a battle reaches the ordinary round cap or reconnects mid-battle
- **THEN** cap remains 100 rounds, round duration six seconds, gauge/upkeep behavior unchanged and reconnect invents no elapsed time

