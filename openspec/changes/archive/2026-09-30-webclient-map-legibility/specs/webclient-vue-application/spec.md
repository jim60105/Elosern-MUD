## MODIFIED Requirements

### Requirement: Chrome type is legible and numerals are stable
At the reference scale chrome text SHALL render at least 12 CSS pixels using the shared local design faces, including the minimap island's title, orientation marks and readout and the full-map overlay's guide, input hint, view controls, legend and remembered list. The only text outside that floor is the drawn map itself — the node labels and edge-marker names inside the island's and the full map's SVG drawing — whose sizes follow the `webclient-local-map` fitted label contract (island node labels at a 12-unit step drawn at 12 × the drawing's scale, island marker names at a 10-unit step). Resource values, costs, counts and prices outside the drawn map SHALL use proportional sans tabular lining numerals. Monospace SHALL remain reserved for command input, ASCII/box-drawing content, key names and the map's own coordinate and label type; prose SHALL retain its existing reader sizing contract, including viewport-relative sizing and prose-scale preferences.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces, the minimap island and the full-map overlay render at 1920x1080
- **THEN** chrome text outside the drawn map meets the 12px floor without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace
