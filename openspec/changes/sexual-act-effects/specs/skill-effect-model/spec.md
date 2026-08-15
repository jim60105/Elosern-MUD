## ADDED Requirements

### Requirement: pleasure and sexual_counter parse into bare-key-carrying typed dataclasses
`world/skills/effects.py`'s `parse_effect` SHALL classify `pleasure:<act_key>` into
`PleasureEffect(act_key)` and `sexual_counter:<act_key>` into `SexualCounterEffect(act_key)`, using
the existing `_parse_single_arg` helper. Each dataclass SHALL carry exactly the one field `act_key:
str` and no other data — magnitude, parts, ratio, and counter names are read from
`SEXUAL_ACT_REGISTRY[act_key]` by the consuming effect handler, never encoded in the effect string.

#### Scenario: A well-formed pleasure effect parses
- **WHEN** `parse_effect("pleasure:masturbation_seed")` is called
- **THEN** it returns `PleasureEffect(act_key="masturbation_seed")`

#### Scenario: A well-formed sexual_counter effect parses
- **WHEN** `parse_effect("sexual_counter:masturbation_seed")` is called
- **THEN** it returns `SexualCounterEffect(act_key="masturbation_seed")`

#### Scenario: A malformed effect with no key raises at construction
- **WHEN** `parse_effect("pleasure:")` is called
- **THEN** it raises `ValueError`, matching every other `_parse_single_arg`-based prefix's existing
  behaviour for a missing argument
