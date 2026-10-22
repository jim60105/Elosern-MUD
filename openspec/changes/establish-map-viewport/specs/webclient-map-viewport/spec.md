# Spec Delta

## Purpose

Provide truthful uniform map projection and navigation geometry for the area/world drawer without changing canonical positions or movement authority.

## ADDED Requirements

### Requirement: Map navigation preserves uniform geometry and the zoom anchor
Map projection SHALL use one uniform scale per viewport and invert the north axis only for screen presentation. Pan and continuous wheel zoom SHALL not alter canonical node coordinates. Zoom at a pointer anchor SHALL preserve the map point under that anchor within numeric tolerance.

#### Scenario: Unequal metric gaps remain unequal
- **WHEN** nodes have unequal metre separations and the viewport pans or zooms
- **THEN** their projected gap ratio is preserved with no row/column rank compression

#### Scenario: Anchored zoom is reversible
- **WHEN** a pointer maps to a world point and zoom changes around that pointer
- **THEN** the same world point remains under it and inverse projection round-trips

### Requirement: Map zoom stops and fit follow scope and aspect ratio
World stops SHALL be continent fit for viewport aspect ratio, country 800 km, district 200 km and nearby 40 km. Settlement stops SHALL be whole city, district and nearby; wilderness stops SHALL be surroundings and nearby. Plus/minus SHALL jump stops while wheel zoom remains continuous. Fit/recentre SHALL operate in the current scope units.

#### Scenario: Continent fit includes the land in a wide viewport
- **WHEN** the world viewport changes aspect ratio and requests whole-map fit
- **THEN** the entire continent fits both axes without distorting relative geometry

#### Scenario: Coordinate-free map remains radial
- **WHEN** an area payload has no room coordinates
- **THEN** no metric coordinates are fabricated for those rooms

### Requirement: Offscreen geometry avoids the selected detail drawer
Quest pointer clamping SHALL use the usable map rectangle excluding an open approximately 360 px detail drawer and floating controls. The same exclusion SHALL guide placement on every edge.

#### Scenario: Selected drawer occludes an offscreen target direction
- **WHEN** a target lies to the right while details are open
- **THEN** the pointer clamps to the usable rectangle left of the drawer and recomputes when details close
