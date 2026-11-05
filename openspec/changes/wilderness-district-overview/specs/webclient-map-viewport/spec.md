# Spec Delta

## MODIFIED Requirements

### Requirement: Map zoom stops and fit follow scope and aspect ratio
World stops SHALL be continent fit for viewport aspect ratio, country 800 km, district 200 km and nearby 40 km. Settlement stops SHALL be whole city, district and nearby; wilderness stops SHALL be the visible window, surroundings and nearby, plus one district-overview fit stop when the payload supplies a lit district overview. Plus/minus SHALL jump stops while wheel zoom remains continuous. Fit/recentre SHALL operate in the current scope units.

#### Scenario: Continent fit includes the land in a wide viewport
- **WHEN** the world viewport changes aspect ratio and requests whole-map fit
- **THEN** the entire continent fits both axes without distorting relative geometry

#### Scenario: Coordinate-free map remains radial
- **WHEN** an area payload has no room coordinates
- **THEN** no metric coordinates are fabricated for those rooms

#### Scenario: District overview widens the wilderness stops
- **WHEN** a wilderness area payload carries a lit district overview
- **THEN** the widest stop fits the union of the overview and the 41-cell window, the opening view stays on the surroundings, and a payload without an overview keeps the existing stops and limits
