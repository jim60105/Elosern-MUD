# Spec Delta

## Purpose

Render authoring map views from in-memory data without a service, using shared drawing with explicit coordinate, camera and visibility semantics.

## ADDED Requirements

### Requirement: Offline map rendering is isolated and map only
The offline renderer SHALL render one selected authoring view from structured in-memory data using shared editor drawing and local assets without service access or mutation behavior.

#### Scenario: Three offline views
- **WHEN** continent, settlement and interior payloads are rendered separately with HTTP/network access denied and no editor service or Node runtime
- **THEN** each draws its selected map with local fonts, colors, glyphs and background, and completion is signaled after fonts, terrain image and layout finish

#### Scenario: Inert content and surface composition
- **WHEN** labels include executable-looking text and scene identifiers resemble URLs
- **THEN** labels remain text, no authored URL is fetched, and the image contains no header, navigation, inspector, diagnostics, tools, zoom controls, frame/status pills, selection, handles, hover effects or focus rings

#### Scenario: Shared editor behavior remains interactive
- **WHEN** the editor uses the extracted shared drawing and a user selects, pans, zooms and moves an editable mark
- **THEN** its existing map display, preferences, selection and interaction behavior remain unchanged

### Requirement: Capture cameras preserve coordinate frames and requested extent
Capture cameras SHALL use declared view coordinates, uniform scale and requested centres, expanding explicit bounds to the output aspect ratio and fitting unfiltered full-map content when bounds are absent.

#### Scenario: Geographic frames
- **WHEN** continent kilometre bounds or settlement local-metre bounds are supplied
- **THEN** X grows east and Y north, continent coordinates convert to scene metres, settlement coordinates stay local, and reported bounds return in the input frame

#### Scenario: Interior down-positive frame
- **WHEN** interior bounds [1,2,5,8] are supplied to a square output
- **THEN** scene Y inversion preserves down-positive stored layout orientation, reported bounds are [0,2,6,8] in layout units, and no geographic units or directions are invented

#### Scenario: Aspect ratio and out-of-map region
- **WHEN** bounds [0,0,10,20] are captured at 200 by 100 pixels, including when they contain no objects or extend beyond the map
- **THEN** reported bounds are [-15,0,25,20], scale is uniform, the centre stays [5,10], the entire requested extent is visible, and no clamping or recentering occurs

#### Scenario: Complete fit and stable hiding
- **WHEN** full-map fitting includes bent roads, room/exterior cards and long labels and layers are subsequently hidden
- **THEN** the original unfiltered extent and visible glyph/label padding determine a camera that does not move when hiding layers; full fit accommodates visible cards/labels while explicit regional views clip at image edges

### Requirement: Capture visibility is view scoped and independent
Capture rendering SHALL default every applicable layer on and hide only explicitly named geometry or labels while preserving independent geometry, existing topology and the fitted camera.

#### Scenario: Continent layers
- **WHEN** each continent layer is independently hidden
- **THEN** terrain controls mainland, terrain/passability raster and forest edge; water controls waterways; ridge controls ridge walls, passes and fords; locations controls locations and reserved harbour sites; footprint controls settlement footprints; partition controls derived national borders and district outlines; labels controls normally drawn names, IDs and connection text

#### Scenario: Settlement and interior layers
- **WHEN** settlement nodes or roads, or interior rooms, connections or exterior are independently hidden
- **THEN** nodes includes gate glyphs, roads includes directed authored bends, rooms includes cards, connections includes within-interior links and existing direction indicators, and exterior includes the existing doorway card and its link; nodes/rooms never implicitly hide roads/connections

#### Scenario: Label independence and empty surface
- **WHEN** labels alone, a geometry layer, or all applicable layers are hidden
- **THEN** label hiding preserves glyph/card geometry and direction indicators, geometry hiding removes its own labels, and hiding everything leaves the normal background at the same camera

#### Scenario: No invented relationships
- **WHEN** a settlement has directed roads and an interior has other relationships currently listed but undrawn
- **THEN** shared drawing retains current topology and connection text without adding new road arrows, undrawn relationships or geographic information
