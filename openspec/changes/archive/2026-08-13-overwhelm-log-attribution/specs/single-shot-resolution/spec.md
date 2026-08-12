# single-shot-resolution Delta Specification

## MODIFIED Requirements

### Requirement: resolve_overwhelm resolves an overwhelm-classified encounter by reusing run_round,
never a separate combat algorithm
`world/rules/overwhelm.py` SHALL provide `resolve_overwhelm(battlefield, action_provider, max_rounds,
commanded_actor=None, commanded_skill=None) -> OverwhelmResult`. Every state mutation this function
causes SHALL occur exclusively through calls to change 9's
`combat.run_round(battlefield, action_provider)`, unmodified. This function SHALL NOT call
`roll_d100()`, construct a `PendingEffect`, or perform any damage/to-hit computation of its own. The
optional `commanded_actor` and `commanded_skill` keyword arguments SHALL be forwarded to
`compress_event_logs()` together with the encounter's round-1 log slice, and SHALL influence only
the compressed log record (the commanded-action marker), never combat math, round count, verdicts,
or any entity state; callers that omit them receive identical resolution with no marker.

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

#### Scenario: The optional commanded identity never changes resolution
- **WHEN** the same `Battlefield` and seed are resolved once with `commanded_actor`/`commanded_skill`
  and once without them
- **THEN** `rounds_elapsed`, `total_seconds`, `verdict_after`, `battle_over`, and every entity's
  final hp are identical between the two calls; the only difference in `event_logs` is the
  commanded-action marker entry
