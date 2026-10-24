# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Recovery waiting preserves skip safety`
- TO: `### Requirement: Owner-targeted sleep continuation preserves skip safety`

## MODIFIED Requirements

### Requirement: Interruptible skips stop at the earliest relevant boundary
Ordinary wait, sleep and eligible study SHALL stop at the earliest involved forced-sleep entry, natural wake target or registered interaction; only elapsed time SHALL commit and unperformed request time SHALL be discarded. The explicit owner-targeted automatic sleep continuation SHALL consume successive physiological boundaries under its retained authorization, stopping at the owner's target or a real interaction/safety interruption. Noninteractive stages SHALL preserve exact consumption.

#### Scenario: First wake
- **WHEN** a forced sleeper at zero is involved in an ordinary 10000-second safe wait
- **THEN** exactly 6000 seconds commits, the undefeated sleeper wakes at 72000, control returns and 4000 seconds of that wait is discarded

#### Scenario: First collapse
- **WHEN** an awake companion has 2400 units during an ordinary requested 1200-second wait
- **THEN** exactly 600 seconds commits, the companion enters forced sleep and the remainder of that wait is discarded

#### Scenario: Registered event
- **WHEN** a real registered interactive event is due in 37 seconds before the next physiological boundary
- **THEN** exactly 37 seconds commits and the event publishes without a random ambush roll; automatic continuation pauses too

#### Scenario: No replay
- **WHEN** an interrupted result is retried with the same accepted interval identity
- **THEN** that interval never replays; ordinary wait needs a new action and owner sleep recovery uses only its retained uncommitted target after interaction is resolved

### Requirement: Owner-targeted sleep continuation preserves skip safety
If every operable present body sleeps, no companion is possessed and the player declines/closes dream entry, recovery SHALL automatically continue the same owner sleep to its duration deadline or declared recovery target. Earlier companion wake SHALL not stop it. Real interaction or combat/hostile safety SHALL interrupt without unsafe skips. A sleeping owner SHALL retain actionable status/recovery/handoff, without ordinary action authority.

#### Scenario: Unsafe collapse
- **WHEN** an accepted indivisible action collapses a body in a hostile room
- **THEN** posture commits with that action, automatic recovery adds no unsafe time and existing engagement/defeat policy remains available

#### Scenario: Safe all asleep
- **WHEN** all operable bodies sleep in safety and the unpossessed player declines or closes the owner dream prompt
- **THEN** the server continues to the owner's accepted target without wait clicks or a nonacting dead end

#### Scenario: Companion wakes earlier
- **WHEN** all-asleep continuation targets owner deadline at tick 7200 and a companion wakes at tick 100
- **THEN** it reconciles companion wake and subsequent awake consumption, then reaches tick 7200 unless a real interaction or safety boundary intervenes

#### Scenario: Interruption recovery
- **WHEN** an actual interactive event interrupts automatic recovery
- **THEN** the committed prefix persists, the event and status expose lawful response plus resume of the same remaining sleep after resolution, and no repeated wait clicks are needed merely to cross wake boundaries

#### Scenario: Awake alternatives after decline
- **WHEN** the owner sleeps without possession but an operable companion is awake when dream entry is declined
- **THEN** no automatic all-asleep continuation starts; refreshed handoff and explicit same-sleep continuation remain available without forcing possession
