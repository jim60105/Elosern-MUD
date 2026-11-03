# Spec Delta

## MODIFIED Requirements

### Requirement: Capture visibility is view scoped and independent
Capture rendering SHALL default every applicable layer on and hide only explicitly named geometry or labels while preserving independent geometry, existing topology and the fitted camera.

#### Scenario: Continent layers
- **WHEN** each continent layer is independently hidden
- **THEN** terrain controls mainland, terrain/passability raster and forest edge; water controls waterways; ridge controls ridge walls, passes and fords; locations controls locations and reserved harbour sites; landmarks controls district landmark marks; footprint controls settlement footprints; partition controls derived national borders and district outlines; labels controls normally drawn names, IDs and connection text

#### Scenario: Settlement and interior layers
- **WHEN** settlement nodes or roads, or interior rooms, connections or exterior are independently hidden
- **THEN** nodes includes gate glyphs, roads includes directed authored bends, rooms includes cards, connections includes within-interior links and existing direction indicators, and exterior includes the existing doorway card and its link; nodes/rooms never implicitly hide roads/connections

#### Scenario: Label independence and empty surface
- **WHEN** labels alone, a geometry layer, or all applicable layers are hidden
- **THEN** label hiding preserves glyph/card geometry and direction indicators, geometry hiding removes its own labels, and hiding everything leaves the normal background at the same camera

#### Scenario: No invented relationships
- **WHEN** a settlement has directed roads and an interior has other relationships currently listed but undrawn
- **THEN** shared drawing retains current topology and connection text without adding new road arrows, undrawn relationships or geographic information
