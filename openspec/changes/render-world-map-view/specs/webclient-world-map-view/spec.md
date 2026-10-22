# Spec Delta

## Purpose

Render the server-filtered world map with legible exploration states, scope-aware detail and accessible precision-aware commission markers.

## ADDED Requirements

### Requirement: World layers render in the approved exploration order
WorldMapView SHALL draw sea, land, lit terrain, unlit hatching, district borders, national borders, coastline, trail, approximate-quest circles, places/landmarks, quest markers, current position, labels and chrome in that order. Lit/unlit states SHALL differ by hatching, line style and text as well as colour; approximate markers SHALL be dashed circles labelled 大致方位.

#### Scenario: Unlit geometry has no invented contents
- **WHEN** the real component receives only an unlit outline and opaque identity
- **THEN** it renders hatching, dotted border and 未探明 without generating a district name, landmark or place

#### Scenario: Approximate commission is perceptibly different
- **WHEN** an approximate marker is supplied
- **THEN** a dashed circle and 大致方位 text convey its precision without deriving an exact point

### Requirement: World map detail follows zoom thresholds without shrinking text
Nation names SHALL appear at continent/country views. Lit district and place names SHALL appear at spans up to 1000 km, and 未探明 labels up to 450 km. Trail SHALL be a line except at nearby view where it is cells. Labels SHALL remain at least 16 CSS px, with lower-priority collisions hidden.

#### Scenario: Threshold boundaries are inclusive
- **WHEN** the span passes 1000 km or 450 km
- **THEN** the relevant labels appear at and below their threshold and disappear above it without reducing font size

#### Scenario: Nearby trail respects supplied resolution
- **WHEN** nearby view receives a downsampled 5 km trail
- **THEN** its cells represent 5 km coverage rather than falsely implying 1 km precision

### Requirement: Newly lit districts animate accessibly from their landmark
When a previously unlit district becomes lit while the drawer is open, it SHALL play a 600 ms ink spread from its landmark and announce 已探明：<district> in a live region. Reduced motion SHALL switch instantly; initial load, repeated payloads or reopening already-lit districts SHALL not replay discovery.

#### Scenario: New discovery update arrives while visible
- **WHEN** a district transitions from unlit to lit in an active map session
- **THEN** one ink spread starts at its landmark and one live announcement is emitted

#### Scenario: Reduced motion or existing knowledge
- **WHEN** reduced motion is active or already-lit data is initially rendered
- **THEN** reduced motion applies instantly and existing knowledge does not produce a new discovery animation/announcement

### Requirement: World selection exposes readable permitted detail
Selecting a permitted district, place or commission SHALL emit semantic selection and mirror its supplied details as text. District detail SHALL list every nominal nation it belongs to, including both nations for the deep forest. Unlit selection SHALL not invent missing details.

#### Scenario: Deep forest is selected after exploration
- **WHEN** the lit deep-forest district is selected
- **THEN** the detail includes both Grandia and Valhalla while the map draws no national border inside the forest
