## MODIFIED Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
The recognized prefix set SHALL additionally include `heal` and `self_heal`. `heal:<shape>` SHALL parse
to a `HealEffect(shape=<shape>)` with `shape` restricted to `"single"` or `"area"`; the bare
`self_heal` SHALL parse to a `SelfHealEffect()`. Both SHALL raise `ValueError` for any payload outside
their declared form, exactly like every other prefix in the set.

#### Scenario: heal and self_heal parse into their dataclasses
- **WHEN** `parse_effect("heal:single")`, `parse_effect("heal:area")`, and
  `parse_effect("self_heal")` are called
- **THEN** they return `HealEffect(shape="single")`, `HealEffect(shape="area")`, and
  `SelfHealEffect()` respectively

#### Scenario: A malformed heal payload raises
- **WHEN** `parse_effect("heal:allies")` or `parse_effect("self_heal:single")` is called
- **THEN** it raises `ValueError`
