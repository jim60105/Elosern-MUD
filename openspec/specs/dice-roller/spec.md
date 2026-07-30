# dice-roller Specification

## Purpose
TBD - created by archiving change dice-combat. Update Purpose after archive.
## Requirements
### Requirement: d100 roller wraps evennia.contrib.rpg.dice directly
`world/rules/dice.py` SHALL provide `roll_d100() -> int`, returning a single integer in `[1, 100]`,
implemented as a thin wrapper over `evennia.contrib.rpg.dice.roll()` (design doc §4: "Use directly").
No module under `world/rules/` SHALL implement its own percentile-die logic outside this wrapper.

#### Scenario: roll_d100 always returns a value in range
- **WHEN** `roll_d100()` is called any number of times
- **THEN** every returned value is an integer `n` with `1 <= n <= 100`

#### Scenario: roll_d100 delegates to the contrib roller, not a bespoke implementation
- **WHEN** `world/rules/dice.py`'s source is inspected
- **THEN** it imports and calls `evennia.contrib.rpg.dice.roll` (or the module's own `roll` entry
  point) rather than implementing percentile-die logic via `random.randint()` or equivalent directly
  in this project's own code

### Requirement: Rolls are reproducible under a fixed seed
Given a fixed random seed, a sequence of `roll_d100()` calls SHALL be reproducible across repeated test
runs — the basis for this change's golden fixed-seed tests (design doc §10).

#### Scenario: The same seed produces the same roll sequence
- **WHEN** the RNG is seeded to a fixed value, `roll_d100()` is called N times, the RNG is reset to the
  identical seed, and `roll_d100()` is called N times again
- **THEN** both sequences of N results are identical, element for element

#### Scenario: Different seeds can produce different sequences
- **WHEN** the RNG is seeded to two different fixed values and `roll_d100()` is called N times under
  each
- **THEN** the two sequences are not required to be identical (no assertion that they must differ, but
  the reproducibility scenario above must hold independently for each seed)

