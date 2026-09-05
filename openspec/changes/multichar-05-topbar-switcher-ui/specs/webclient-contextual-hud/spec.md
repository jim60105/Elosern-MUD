# Delta spec: webclient-contextual-hud (multichar-05-topbar-switcher-ui)

The stage's top band gains a third element. The anchor/band non-overlap requirement is restated so
the band's own contents are covered at both asserted viewports, and so a transient popover is
explicitly distinguished from a layout element.

## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the narrative caption card above it, the HUD islands above that, the action dock
above those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed
by named stage anchors (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`) rather than by fixed
layout columns, and SHALL NOT be placed inside a scrolling container that can push a required surface
out of view. The dock's reserved height SHALL come from the shared `--dock-h` token, and the narrative
caption and the right-hand HUD stack SHALL be positioned relative to it so they never overlap it. At
both 1440x900 and 1280x720 no stage anchor SHALL overlap another anchor's content, and the top band's
own elements SHALL neither overlap one another nor extend into the HUD island anchor region: a band
element whose content is variable-width SHALL be bounded and truncated rather than sized by its
content. A transient popover opened from a top-band element MAY overlay the island anchors while
open, provided it does not change the band's own rendered box and closes on Escape and on outside
activation; a surface that permanently occupies vertical space SHALL NOT be introduced into the band
this way.

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1440x900
- **THEN** the scene backdrop fills the viewport, and the narrative caption, the HUD islands, the action dock, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height
- **THEN** the island stack itself is bounded and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every mode-visible surface present
- **THEN** no stage anchor's rendered box intersects another anchor's rendered box

#### Scenario: The top band's own elements do not collide
- **WHEN** the shell renders at 1280x720 with every top-band element present and a maximum-length character name committed
- **THEN** the band's elements render side by side without intersecting, the variable-width element is truncated within its bound, and no band element's box extends into the island anchor region

#### Scenario: A band popover overlays without displacing
- **WHEN** a transient popover is opened from a top-band element
- **THEN** the band's rendered box is unchanged, the popover renders above the island anchors, and Escape or outside activation closes it
