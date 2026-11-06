## ADDED Requirements

### Requirement: Monster spawn layer draws zones and sites on the continent
The continent SHALL offer a monster spawn layer, hidden by default and absent from other domains, that draws one polygon per zone rectangle over its inclusive cells, one fixed-size mark per zone and one fixed-size mark per site, from exported data only and with no permanent text labels.

#### Scenario: Hidden by default
- **WHEN** the continent opens with a synthetic section and the author then shows the layer
- **THEN** no monster drawable appears until the layer is shown, and showing it adds only monster drawables

#### Scenario: Inclusive rectangle edges
- **WHEN** a synthetic zone rectangle covers cells `x_min..x_max` and `y_min..y_max` at a given cell size
- **THEN** its polygon spans `x_min` to `x_max + 1` and `y_min` to `y_max + 1` in cells, converted to metres with that cell size

#### Scenario: Multi-rectangle zone
- **WHEN** a synthetic zone holds two rectangles
- **THEN** two polygons and one mark share the zone's reference, and the mark sits at the centre of the first rectangle

#### Scenario: Site marks
- **WHEN** synthetic sites of every kind are drawn
- **THEN** each mark sits at its cell's centre and each kind has a distinct glyph

#### Scenario: Labels stay out of the map surface
- **WHEN** the layer is shown in the browser
- **THEN** monster marks render no text element and expose their label through a hover title

#### Scenario: Composed labels
- **WHEN** synthetic rows repeat a species across pool rows, or a site names an individual
- **THEN** the zone label lists each species once in first-seen pool order, and the site label uses the individual name in place of species names
