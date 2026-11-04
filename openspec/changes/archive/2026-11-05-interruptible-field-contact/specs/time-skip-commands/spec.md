# Spec Delta

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

#### Scenario: Actual hostile contact
- **WHEN** a long wait, rest, study, camp or accepted sleep encounters its first projected hostile contact before its requested endpoint
- **THEN** only accepted time/recovery commits and unused time is discarded; distant maintenance is internal, voluntary sleep interrupts its receipt and forced sleep preserves its threshold

#### Scenario: Separate hostile continuation
- **WHEN** no party member can act after the accepted interval ends in combat
- **THEN** normal enemy-only rounds are separately accounted combat time, never unused skip duration or extra sleep receipt recovery
