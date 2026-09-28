## ADDED Requirements

### Requirement: Chrome type is legible and numerals are stable
At the reference scale chrome text outside the map anchors SHALL render at least 12 CSS pixels using the shared local design faces. Resource values, costs, counts and prices outside those anchors SHALL use proportional sans tabular lining numerals. Monospace SHALL remain reserved for command input, ASCII/box-drawing content and key names outside those anchors; prose SHALL retain its existing reader sizing contract, including viewport-relative sizing and prose-scale preferences.

Approved deferral (2026-09-28): the map island and full-map drawing and chrome, including titles and readouts, remain owned by A12 `webclient-map-legibility`. A3 only replaces their shared token references with local fixed values of identical size, without changing their appearance. Their current type-ladder browser contract remains in force until A12 implements that migration.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces render at 1920x1080
- **THEN** chrome text outside the map anchors meets the 12px floor without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace
