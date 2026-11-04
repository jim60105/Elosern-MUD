# Spec Delta

## ADDED Requirements

### Requirement: Incapacitated hostile parties receive normal enemy rounds
A nonterminal hostile encounter with no actionable ally SHALL resolve and pay normal enemy-only rounds until an ally becomes actionable or the ordinary terminal policy applies, preserving forced-sleep thresholds and stopping automatic play immediately when choice returns.

#### Scenario: One real wake round
- **WHEN** a forced sleeper starts71928 and one real six-second sleep interval reaches72000 while enemies attack normally
- **THEN** its existing receipt/threshold authorizes wake, enemy effects and ordinary upkeep occur once, and automatic continuation stops for a normal player choice

#### Scenario: Temporary incapacity and terminal outcome
- **WHEN** all allies are sleeping or action-blocked but not ordinarily defeated
- **THEN** real enemy rounds continue until eligibility, ordinary defeat/victory or existing cap; sleep alone never declares defeat or immunity

#### Scenario: Examination and invalid request
- **WHEN** a designated exam has its all-forced opening or voluntary sleeping initiation has invalid authority
- **THEN** exam keeps its existing FAIL policy and invalid voluntary initiation rejects before session/time changes

#### Scenario: Failure and retry
- **WHEN** a fault follows actual automatic-round enemy, fatigue, cursor or session writes
- **THEN** the complete DB/live state restores and retry/restart pays and resolves each accepted round once

## MODIFIED Requirements

### Requirement: Combat time settles once at terminal session outcome
Interactive rounds SHALL defer combat time until terminal settlement except for paid incapacitated-hostile continuation; a durable settled-round cursor SHALL charge each six-second round and its actual mental intervals once, preserve recorded occurrence times and clear terminal session state idempotently.

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

#### Scenario: Population loss carries actual round offset
- **WHEN** a mapped session records a defeat in a later round before terminal-only clock settlement
- **THEN** the persisted start tick and completed-round offset identify its occurrence for delayed population settlement, without advancing the live clock early or double-settling rounds

#### Scenario: Paid automatic prefix
- **WHEN** enemy-only continuation pays prior unpaid rounds and its next real round, then ordinary play later terminates
- **THEN** the clock, gauges and physiology pay that prefix once and terminal settlement pays only remaining rounds; restart replay cannot pay it again

### Requirement: No eligible actors leaves command collection paused with explicit party exits
No-actionable-ally hostile combat SHALL continue normal enemy-only rounds through the rules owner until an ally can act or combat terminates; inspection/editing SHALL run no rounds. Confirmed surrender and requested retreat retain their existing authority and no-acting-ally outcome.

#### Scenario: All members action forbidden
- **WHEN** transient capability rules other than the all-forced-sleep opening leave no member eligible to choose a command
- **THEN** the rules continuation executes normal hostile enemy-only rounds until eligibility returns or a terminal policy applies; reconnect or preview itself executes no draft

### Requirement: Live rounds do not simulate natural fatigue or awakening
Ordinary interactive rounds SHALL retain deferred natural fatigue; paid enemy-only hostile rounds SHALL settle actual physiology and release undefeated forced sleepers only at the authored threshold, retaining the existing round duration and cap.

#### Scenario: Threshold sleeper
- **WHEN** a sleeper just below the wake threshold completes ordinary interactive rounds with an awake actionable ally
- **THEN** reserve and posture remain unchanged, no natural wake timer runs, and normal targeting remains available

#### Scenario: Future explicit boundary
- **WHEN** a synthetic explicit posture change is recorded at a round boundary
- **THEN** eligibility can change without a permanent sleep lock, without ticking fatigue or advancing the clock; no waking ability is authored

### Requirement: Terminal mental accounting records actual round-boundary posture intervals
Session accounting SHALL retain actual posture intervals and a paid-round cursor, settle only unpaid awake/sleep durations at terminal outcome and avoid retrospective recovery or duplicate consumption of previously settled hostile rounds.

#### Scenario: Ten rounds awake
- **WHEN** a continuously awake survivor starts at 360 reserve units (0.1%) and completes ten rounds
- **THEN** live reserve stays 360; terminal 60-second consumption clamps it to zero and forced sleep starts after commit with no retrospective recovery

#### Scenario: Ten rounds asleep
- **WHEN** an undefeated sleeper starts at 71280 units and completes ten rounds
- **THEN** only terminal settlement adds 720 units (0.2%), reaching 72000 and waking into moderate fatigue

#### Scenario: Explicit interval split
- **WHEN** a synthetic explicit effect changes a member from asleep to awake after four of ten rounds
- **THEN** terminal accounting restores 24 seconds and consumes 36 seconds, a net loss of 144 units rather than crediting the entire fight as sleep

### Requirement: Terminal physiology cannot reverse defeat and prompts follow aftermath
Mental recovery SHALL preserve defeat/aftermath and never revive dead bodies; undefeated forced sleepers SHALL wake only at their threshold during paid hostile continuation or terminal settlement, and post-commit handoff SHALL use actual survivors.

#### Scenario: Defeated sleeper
- **WHEN** terminal sleep recovery would cross 20% for an actor already established defeated
- **THEN** defeat and ordinary aftermath remain authoritative and no revival or eligible handoff is fabricated

#### Scenario: Stationary victory
- **WHEN** an undefeated forced sleeper remains below 72000 after terminal recovery
- **THEN** it stays asleep and all party travel remains blocked; awake local play remains available

#### Scenario: Late companion removal
- **WHEN** terminal aftermath removes or defeats a previously listed candidate
- **THEN** no prompt includes that candidate and no pre-commit transfer is offered

## REMOVED Requirements

### Requirement: All-forced-sleep engagement enters ordinary zero-round defeat
**Reason**: The approved hostile-contact design requires real enemy actions and physiological wake thresholds instead of defeat caused by sleep alone.

**Migration**: Migrate hostile callers and substantive annotations to normal incapacitated-hostile rounds using generated identifiers; retain the designated examination FAIL path and voluntary-action sleep gates without compatibility fallback.
