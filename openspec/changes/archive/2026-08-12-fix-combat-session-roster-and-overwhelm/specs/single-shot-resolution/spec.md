## MODIFIED Requirements

### Requirement: Single-shot resolution is exactly consistent with per-round resolution under the same
seed and starting state
Given a fixed random seed and an identical starting `Battlefield`, the sequence of entity-state
mutations (hp, buffs, sexual state) produced by `resolve_overwhelm()` SHALL be identical to the
sequence produced by calling `combat.run_round()` the same number of times, in a loop external to this
change, under the same seed and starting state. This SHALL be demonstrated for the player-overwhelming
direction. The foe-overwhelming (reverse) direction is not a dispatchable outcome: the session facade
never invokes `resolve_overwhelm()` for it, so no reverse-equivalence contract exists.

#### Scenario: Final hp values are identical between the two resolution paths
- **WHEN** an overwhelm-classified `Battlefield` is resolved once via `resolve_overwhelm()` under a
  fixed seed, and once by manually calling `combat.run_round()` in a loop the same number of times
  under the identical seed and an identical copy of the starting `Battlefield`
- **THEN** every entity's final `hp` value is identical between the two paths

#### Scenario: The uncompressed sequence of EventLog entries is identical between the two resolution paths
- **WHEN** the same two resolution paths from the prior scenario are compared using
  `resolve_overwhelm()`'s internal, pre-compression `EventLog` sequence
- **THEN** that sequence is entry-for-entry identical to the manually driven path's collected
  `EventLog`s, including every `"roll"`-kind entry's recorded value

#### Scenario: rounds_elapsed and the winner are identical between the two resolution paths
- **WHEN** the same two resolution paths are compared to completion (encounter ends in both)
- **THEN** `rounds_elapsed` is identical between the two paths, and the same team is left with living,
  non-fled members in both

## ADDED Requirements

### Requirement: The session never dispatches compression for the foe-overwhelming direction
The player-combat session SHALL invoke `resolve_overwhelm()` only for player-overwhelming verdicts; a
foe-overwhelming verdict SHALL NOT be passed to the resolver by any production call site.

#### Scenario: Foe-overwhelming encounters never reach the resolver in production
- **WHEN** every production call site of `resolve_overwhelm()` is inspected
- **THEN** each is gated on the player's team being the overwhelming side, and no call site passes a foe-team verdict
