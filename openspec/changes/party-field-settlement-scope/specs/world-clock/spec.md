# Spec Delta

## MODIFIED Requirements

### Requirement: advance() settles exactly the entities its caller supplies, never a global registry
`WorldClock.advance(seconds, source, entities)` SHALL apply the per-entity settlement stages (gauge
regen; buff ticks and sexual decay, subject to the `AdvanceSource` gate) only to the `entities`
iterable the caller supplies. `advance()` SHALL NOT query any global entity registry, database-wide
scan, or `evennia`-wide object search to discover additional entities to settle.

#### Scenario: Only the supplied entities are settled
- **WHEN** `advance()` is called with `entities=[actor]`, and a different `LivingEntity` exists
  elsewhere in the database with an active buff
- **THEN** that other entity's buff state is unchanged after the call — only `actor`'s state reflects
  settlement

#### Scenario: The registered call sites pass their documented scopes
- **WHEN** `CmdCast`'s integration, out-of-combat item use, and the skip commands call `advance()`
- **THEN** each passes the acting character's present party scope, `charge_movement()` passes the
  travelling party, and `settle_combat_result()` passes `entities=battlefield.roster.values()`

### Requirement: CmdCast advances command time only outside a persistent combat session
`commands/action.py::CmdCast` SHALL settle a successful out-of-combat `ActionResolver.resolve()` call
and its command-time charge inside one outer settlement transaction
(`world/rules/cast_settlement.settle_out_of_combat_cast`, the cast-settlement-atomicity capability):
`CmdCast` SHALL NOT call `WorldClock.advance()` directly, and SHALL NOT advance when the resolution is
rejected. During an active persistent combat session, CmdCast SHALL NOT advance command time.

#### Scenario: A successful out-of-combat cast advances its reported command time
- **WHEN** CmdCast resolves an out-of-combat skill successfully with `time_cost_seconds == 6`
- **THEN** WorldClock tick increases by exactly 6 with `AdvanceSource.COMMAND`, committed together with
  the skill effect, practice award, and planner writes in the same outer transaction

#### Scenario: A rejected out-of-combat cast does not advance the clock
- **WHEN** CmdCast resolves an out-of-combat skill cast that is rejected
- **THEN** WorldClock tick is unchanged and no effect, practice, or planner write commits

#### Scenario: A failed clock settlement leaves the cast uncommitted
- **WHEN** the clock callback or the final clock persistence raises after a successful resolution of an
  out-of-combat cast (for example `status_disguise`)
- **THEN** the failure propagates and the previously committed action state is rolled back too: the
  disguise/practice surfaces equal their pre-action values and the tick is unchanged

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

#### Scenario: Settlement nests resolve and advance in one transaction
- **WHEN** the settlement runs for an out-of-combat cast
- **THEN** it invokes `ActionResolver.resolve()` and, only on success,
  `WorldClock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, entities=present_party_scope(self.caller))` as
  nested operations inside the single outer transaction, committing only after both succeed

#### Scenario: An active-session cast is delegated to session orchestration
- **WHEN** a player submits a cast during an active persistent combat session
- **THEN** CmdCast delegates the selected request to combat-session orchestration and advances no
  command time

#### Scenario: Completed round time accumulates until terminal settlement
- **WHEN** combat rounds complete during a session
- **THEN** their time accumulates in the session and advances exactly once through
  `settle_combat_result(..., AdvanceSource.COMBAT)` at terminal settlement
