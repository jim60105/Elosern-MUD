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
- **WHEN** `CmdCast`'s integration and the skip commands call `advance()`
- **THEN** `CmdCast` passes `entities=[caller]`, the skip commands pass the caller's present party
  scope, `charge_movement()` passes the travelling party, and `settle_combat_result()` passes
  `entities=battlefield.roster.values()`
