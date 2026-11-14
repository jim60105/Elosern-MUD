## MODIFIED Requirements

### Requirement: Chrome type is legible and numerals are stable
Every visible text in the client — chrome text, the drawn-map text, and the message/log prose — SHALL render at the reference scale at 16 CSS pixels or more using the shared local design faces; no shared type token, and no surface, SHALL carry a reference-scale type step below 16 CSS px.

#### Scenario: Dense chrome remains readable
- **WHEN** exploration, dialogue, combat and reference surfaces, the minimap island and the full-map overlay render at the 1451x790 reference viewport
- **THEN** every visible text — chrome text, drawn-map node labels and edge-marker names, and message/log prose — computes to at least 16 CSS px without clipping controls or losing labels

#### Scenario: Values change without terminal styling
- **WHEN** resource/count values change digit widths
- **THEN** their numeric columns remain aligned using tabular figures without switching the surrounding UI to monospace

#### Scenario: Islands and overlays carry no sub-floor steps
- **WHEN** the minimap island's title and readout and the full-map overlay's guide, input hint, view controls, legend and remembered list render
- **THEN** each carries a reference-scale type step of at least 16 CSS px

#### Scenario: The drawn map meets the floor through the fitted label contract
- **WHEN** the node labels and edge-marker names inside the island's and the full map's SVG drawing render
- **THEN** they meet the 16 CSS px floor through the `webclient-local-map` fitted label contract (island node labels at a 16-unit step drawn at 16 × the drawing's scale at the reference scale, island marker names at the matching 16-unit marker step)

#### Scenario: Values use tabular lining numerals
- **WHEN** resource values, costs, counts and prices outside the drawn map render
- **THEN** they use proportional sans tabular lining numerals

#### Scenario: Monospace keeps its role surfaces
- **WHEN** command input, ASCII/box-drawing content, key names, the map's own coordinate and label type, the message window's page text and the full log's lines render
- **THEN** monospace remains their face, as `webclient-contextual-hud` and `webclient-input-narrative` define

#### Scenario: Prose keeps its reader sizing contract
- **WHEN** message and log prose renders
- **THEN** it retains its existing reader sizing contract, including its prose-scale preference

#### Scenario: Proportional em steps are re-stepped to the floor
- **WHEN** a treatment expresses its size relative to the surrounding prose (an `em` step such as a `sys` line's or the box-drawing art path's)
- **THEN** it is re-stepped so its computed size at the reference scale with the default prose scale is at least 16 CSS px

#### Scenario: Reader steps stay above the floor and hidden glyphs are exempt
- **WHEN** a reader-selectable size step is applied
- **THEN** no step drives visible text below the 16 CSS px floor, and `visibility: hidden` spacing glyphs are not visible text and are exempt
