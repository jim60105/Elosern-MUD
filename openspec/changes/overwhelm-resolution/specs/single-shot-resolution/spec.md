## ADDED Requirements

### Requirement: resolve_overwhelm resolves an overwhelm-classified encounter by reusing run_round,
never a separate combat algorithm
`world/rules/overwhelm.py` SHALL provide `resolve_overwhelm(battlefield, action_provider, max_rounds)
-> OverwhelmResult`. Every state mutation this function causes SHALL occur exclusively through calls to
change 9's `combat.run_round(battlefield, action_provider)`, unmodified. This function SHALL NOT call
`roll_d100()`, construct a `PendingEffect`, or perform any damage/to-hit computation of its own.

#### Scenario: resolve_overwhelm performs no combat math outside of run_round
- **WHEN** `world/rules/overwhelm.py`'s source is inspected
- **THEN** it contains no call to `roll_d100()`, no reimplementation of the to-hit or damage formulas,
  and no direct write to any entity's `traits`, `buffs`, or `sexual` state — every such mutation is
  reachable only via `combat.run_round()`

#### Scenario: resolve_overwhelm on an already-contested battlefield performs zero rounds
- **WHEN** `resolve_overwhelm()` is called on a `Battlefield` for which `classify_overwhelm()` already
  returns `None`
- **THEN** it returns an `OverwhelmResult` with zero rounds elapsed, zero total_seconds, and an empty
  `event_logs` tuple, without calling `combat.run_round()` even once

#### Scenario: resolve_overwhelm on an already-concluded battlefield performs zero rounds
- **WHEN** `resolve_overwhelm()` is called on a `Battlefield` for which `combat.is_battle_over()`
  already returns `True`
- **THEN** it returns an `OverwhelmResult` with zero rounds elapsed and `battle_over=True`, without
  calling `combat.run_round()`

### Requirement: Single-shot resolution is exactly consistent with per-round resolution under the same
seed and starting state
Given a fixed random seed and an identical starting `Battlefield`, the sequence of entity-state
mutations (hp, buffs, sexual state) produced by `resolve_overwhelm()` SHALL be identical to the
sequence produced by calling `combat.run_round()` the same number of times, in a loop external to this
change, under the same seed and starting state. This SHALL be demonstrated for both overwhelm
directions.

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

#### Scenario: Reverse overwhelm is proven with the same rigor as forward overwhelm
- **WHEN** a `Battlefield` where the player-aligned team is the overwhelmed side (design doc §6.3's
  "player is one-shot") is resolved via both paths under a fixed seed
- **THEN** the same hp, winner, rounds-elapsed, and entry-for-entry EventLog equivalence checks as the
  forward-overwhelm scenarios all hold

### Requirement: resolve_overwhelm stops the moment classify_overwhelm's verdict changes
`resolve_overwhelm()` SHALL call `classify_overwhelm(battlefield)` before running each round via
`combat.run_round()`, and SHALL stop running further rounds the moment this recomputed verdict differs
from the verdict computed when `resolve_overwhelm()` was first called, reporting the new verdict via
`OverwhelmResult.verdict_after` without asserting or acting on it further.

#### Scenario: A mid-fight power-tier shift ends single-shot resolution early
- **WHEN** an overwhelm-classified encounter's classification changes after some number of rounds
  (e.g. because `combat.run_round()`'s own per-round upkeep changes a combatant's `effective_value()`
  output enough to flip `classify_overwhelm()`'s result)
- **THEN** `resolve_overwhelm()` stops calling `combat.run_round()` at that point, and
  `OverwhelmResult.rounds_elapsed` reflects only the rounds actually run under the original
  classification

#### Scenario: verdict_after distinguishes a flip to contested from a flip to the opposite direction
- **WHEN** `resolve_overwhelm()` stops early due to a classification change
- **THEN** `OverwhelmResult.verdict_after` reports the exact new value `classify_overwhelm()` returned
  (`None` for contested, or the other team's key for a reversed direction), distinct from
  `OverwhelmResult.overwhelming_team`, which always reports the verdict at entry

### Requirement: A finite max_rounds safety cap is a named, tested outcome, not an implicit assumption
`resolve_overwhelm(battlefield, action_provider, max_rounds)` SHALL stop calling `combat.run_round()`
once `rounds_elapsed` reaches `max_rounds`, regardless of whether `classify_overwhelm()` still returns
the original verdict, and SHALL report the resulting `OverwhelmResult` with `battle_over` reflecting
`combat.is_battle_over()`'s true value at that point (not assumed `True`) and `total_seconds` equal to
the honest `rounds_elapsed * 6` for however many rounds actually ran — never a flat, fixed charge
regardless of `rounds_elapsed`.

#### Scenario: Hitting max_rounds stops the loop and reports the true, unfinished state honestly
- **WHEN** a fixture is constructed where `classify_overwhelm()` continues returning the same verdict
  every round for longer than `max_rounds`
- **THEN** `resolve_overwhelm()` stops calling `combat.run_round()` at exactly `max_rounds` rounds,
  `OverwhelmResult.battle_over` is `False` (the encounter has not actually concluded), and
  `OverwhelmResult.rounds_elapsed == max_rounds`

#### Scenario: total_seconds is always the honest sum of rounds actually run, never a flat charge
- **WHEN** `resolve_overwhelm()` concludes after any number of rounds — one, several, or exactly
  `max_rounds` — for any of the golden fixtures this change defines
- **THEN** `OverwhelmResult.total_seconds` equals `rounds_elapsed * 6` in every case, and no code path in
  `resolve_overwhelm()` reports a fixed number regardless of `rounds_elapsed`

### Requirement: Reported time cost uses the identical rounds-times-six-seconds formula, unedited
`OverwhelmResult.total_seconds` SHALL equal `rounds_elapsed * 6`, the identical formula
`combat.run_battle()` already uses. No function in `world/rules/overwhelm.py` SHALL call
`WorldClock.advance()` or any equivalent.

#### Scenario: A single-round overwhelm resolution reports 6 seconds
- **WHEN** `resolve_overwhelm()` completes after exactly 1 round
- **THEN** `total_seconds == 6`

#### Scenario: No WorldClock call exists anywhere in this change's code
- **WHEN** `world/rules/overwhelm.py`'s source is inspected
- **THEN** it contains no reference to `WorldClock` and no call to anything named `advance()`

### Requirement: A golden fixed-seed case demonstrates single-round completion for this project's own
calibrated overwhelm matchup
`world/rules/tests/` SHALL contain a fixed-seed test using the elf-versus-human-elite reference
matchup from `dice-combat`'s design.md D-4, asserting `resolve_overwhelm()` concludes the encounter in
exactly 1 round for that fixture, as a concrete demonstration that design doc §6.3's literal "ends in
one round" language holds for this project's real calibrated stat bands.

#### Scenario: The elf-vs-human-elite fixture resolves in exactly one round
- **WHEN** the golden fixture (elf attacker, human-elite defender, per dice-combat design.md D-4's
  worked reference stats) is resolved via `resolve_overwhelm()` under its fixed seed
- **THEN** `rounds_elapsed == 1` and the human-elite defender's final hp is `<= 0`
