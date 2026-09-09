## ADDED Requirements

### Requirement: resolve_overwhelm accepts a first-actor override that applies to round one only
`world/rules/overwhelm.py`'s `resolve_overwhelm()` SHALL accept a keyword-only
`first_actor: str | None = None` and SHALL forward it to `combat.run_round()` for the first round it
runs only — the same `rounds == 0` slice `_resolve_overwhelm_raw()` already uses to capture the
commanded-action marker window. Every subsequent round SHALL be run with `first_actor=None`, so
ordinary initiative governs the rest of the compressed encounter. When `first_actor` is `None`,
`resolve_overwhelm()` SHALL forward nothing new, preserving the existing discipline that a
default-mode caller's call into `run_round()` is byte-identical to the pre-change signature.

#### Scenario: The override reaches round one and no later round
- **WHEN** `resolve_overwhelm()` runs three rounds with `first_actor=key`
- **THEN** the first `combat.run_round()` call receives `first_actor=key` and the second and third
  receive `first_actor=None`

#### Scenario: A default-mode call is unchanged
- **WHEN** `resolve_overwhelm()` is called with `first_actor` omitted and with every other policy
  flag at its default
- **THEN** its call into `combat.run_round()` passes exactly the arguments it passed before this
  parameter existed

### Requirement: The first-actor override influences turn order alone, never resolution outputs
`resolve_overwhelm(first_actor=...)` SHALL NOT change any damage or to-hit computation, the
`classify_overwhelm()` verdict recomputed after each round, `OverwhelmResult.rounds_elapsed`,
`OverwhelmResult.total_seconds`, `OverwhelmResult.overwhelming_team`, or
`OverwhelmResult.verdict_after` other than through the ordinary consequences of the reordered turn
sequence itself. `total_seconds` SHALL remain `rounds_elapsed * 6` in every case.

#### Scenario: Reported time stays the honest rounds-times-six formula
- **WHEN** `resolve_overwhelm()` concludes with a `first_actor` override after any number of rounds
- **THEN** `OverwhelmResult.total_seconds` equals `rounds_elapsed * 6`

#### Scenario: The override adds no combat math of its own
- **WHEN** `world/rules/overwhelm.py`'s source is inspected after this change
- **THEN** it still contains no call to `roll_d100()`, no `PendingEffect` construction, and no
  to-hit or damage computation, and the override is expressed solely as an argument passed through
  to `combat.run_round()`

#### Scenario: A stale override key does not disturb resolution
- **WHEN** `resolve_overwhelm()` is called with a `first_actor` naming an entity that is not an
  eligible actor in round one
- **THEN** resolution proceeds in ordinary initiative order without raising, and every
  `OverwhelmResult` field is what the same seed and starting state produce with `first_actor=None`
