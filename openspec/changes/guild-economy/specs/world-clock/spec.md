## MODIFIED Requirements

### Requirement: CmdCast advances command time only outside a persistent combat session
`commands/action.py::CmdCast` SHALL call `WorldClock.advance(result.time_cost_seconds,
AdvanceSource.COMMAND, entities=[self.caller])` after a successful out-of-combat
`ActionResolver.resolve()` call and SHALL NOT call `advance()` when that resolution is rejected. During
an active persistent combat session, CmdCast SHALL delegate the selected request to combat-session
orchestration and SHALL NOT advance command time. Completed combat rounds SHALL accumulate in the
session and advance exactly once through `settle_combat_result(..., AdvanceSource.COMBAT)` at terminal
settlement.

#### Scenario: A successful out-of-combat cast advances its reported command time
- **WHEN** CmdCast resolves an out-of-combat skill successfully with `time_cost_seconds == 6`
- **THEN** WorldClock tick increases by exactly 6 with `AdvanceSource.COMMAND`

#### Scenario: A rejected out-of-combat cast does not advance the clock
- **WHEN** CmdCast resolves an out-of-combat skill cast that is rejected
- **THEN** WorldClock tick is unchanged

#### Scenario: Active-session cast does not advance command time
- **WHEN** a player submits a preflight-valid cast during an active combat session
- **THEN** CmdCast performs no `AdvanceSource.COMMAND` advance, regardless of the selected skill's
  ordinary command time

#### Scenario: Rejected active-session input does not advance time
- **WHEN** combat-session preflight rejects the selected action before initiative
- **THEN** neither command nor combat time advances

#### Scenario: Terminal session settles all round time once
- **WHEN** a combat session terminates after three completed six-second rounds
- **THEN** `settle_combat_result()` advances exactly 18 seconds with `AdvanceSource.COMBAT` and no earlier
  in-session CmdCast added command time
