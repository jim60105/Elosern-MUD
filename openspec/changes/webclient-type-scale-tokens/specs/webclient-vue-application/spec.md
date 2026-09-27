## ADDED Requirements

### Requirement: Chrome type is legible and numerals are stable
At the reference scale chrome text outside map drawing geometry SHALL render at least 12 CSS pixels using the shared local design faces. Resource values, costs, counts and prices SHALL use proportional sans tabular lining numerals. Monospace SHALL remain reserved for command input, ASCII/box-drawing content and key names; prose SHALL retain its existing viewport-relative reader contract.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces render at 1920x1080
- **THEN** chrome text outside the map drawing meets the 12px floor without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace
