# Spec Delta

## MODIFIED Requirements

### Requirement: Travel painting uses disclosed cell facts
The travel map SHALL paint deterministic terrain and reveal layers from committed decoded facts, keep unknown ground transparent and update camera or overlays without repainting the terrain. A supplied lit district overview SHALL paint behind the local window, clipped out of that window, at the same explored grade and light phase.

#### Scenario: Disclosure and compositing
- **WHEN** synthetic unknown, memory, live and district-overview cells include bands, roads, rivers, ford, woods, districts and settlement edges
- **THEN** unknown pixels and clipped strokes remain transparent, supplied live/memory/phase facts control lighting and repeated identical input is deterministic

#### Scenario: Invalidation and repaint budget
- **WHEN** content changes at the two acceptance viewports and then only camera, zoom, aim or hover changes
- **THEN** one coalesced repaint occurs for content changes, none for transform/overlay-only changes and each warmed measured repaint takes at most50ms

#### Scenario: District overview cannot bleed into the fine window
- **WHEN** a coarse overview cell straddles an unrevealed 41-cell fine cell
- **THEN** the fine window rectangle is cleared from the overview layer, the fine cell stays transparent, and no coarse terrain or double-blended grade appears inside it

#### Scenario: Night changes the overview grade
- **WHEN** the supplied light phase changes while a district overview is shown
- **THEN** the overview repaints with the same desaturation, memory dim and wash as the fine explored cells

### Requirement: Travel camera preserves the open stage
The travel camera SHALL follow the party or fit a locked route within measured open-stage bounds, keep the 18..46 px per km local ladder and, when a district overview is supplied, add one symbolic district-fit state that shows the whole district. Glide and token breathing SHALL be omitted at off motion.

#### Scenario: Follow and fit
- **WHEN** synthetic route bounds, viewport dimensions and side-column sizes change
- **THEN** camera centres or fits within the safe rectangle with minimum14px cells for fitting and zoom18..46px in4px steps at the current UI scale

#### Scenario: Approximate edge observations
- **WHEN** bearing-only sightings have no source coordinates and open-stage exclusions change
- **THEN** cards project to its inset edge without acquiring target coordinates or covering band/header/side controls

#### Scenario: Whole district fit
- **WHEN** the player selects the district-fit state for a supplied overview
- **THEN** the union of the overview and the 41-cell window fits inside the safe rectangle, neighbour targets and single-click stepping are suppressed, the scale bar chooses a readable step, and leaving fit returns to 18 px per km

#### Scenario: District change resets fit
- **WHEN** the committed overview becomes null or names a different district while the camera is at the district-fit state
- **THEN** the camera leaves fit, returns to the local ladder and never keeps an orphaned sub-18 scale
