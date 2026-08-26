## MODIFIED Requirements

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with
cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and
labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's
gradient stage otherwise — for a missing, failed, or invalid asset, for a pending scene with no prior
image, and when the `art` panel is unavailable. The backdrop SHALL NOT present an invented image and
SHALL NOT present a stale image as current. The scene label, its alternative text, and any truthful
placeholder label SHALL be rendered as text outside the bitmap, so no required information exists only
inside an image. The gradient stage SHALL differ per mode (exploration, dialogue, combat) and SHALL
carry an inset vignette.

The backdrop's own floating caption elements (the truthful-placeholder card, the `目前場景圖片生成中`
pending notice, the scene label and alternative-text captions, and the full-view control) SHALL be
positioned so that none of them overlaps the action dock's or the command line's rendered content, at
both 1440x900 and 1280x720 — extending the sibling stage requirement's general anchor non-overlap
invariant to these backdrop-internal captions, which sit outside the five named stage anchors but are
absolutely positioned within the same full-bleed stage.

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

#### Scenario: A missing scene degrades to the mode gradient
- **WHEN** the committed art panel carries a missing, failed, or invalid scene
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as text, and no image element carries a URL

#### Scenario: An unavailable art panel is indistinguishable from an ungenerated scene
- **WHEN** the `art` panel commits its unavailable form
- **THEN** the backdrop renders the mode gradient stage exactly as for a missing asset, with no broken image frame and no gameplay surface blocked

#### Scenario: A pending scene keeps its prior image labelled
- **WHEN** the scene is pending and a prior scene image is already rendered
- **THEN** the backdrop keeps that image visibly dimmed with the explicit `目前場景圖片生成中` label, and never presents it as the current scene

#### Scenario: The combat stage is visually distinct
- **WHEN** the committed mode is combat and no scene image is available
- **THEN** the backdrop renders the combat gradient stage, visually distinct from the exploration stage

#### Scenario: The truthful-placeholder caption never intrudes on the action dock
- **WHEN** the `art` panel is unavailable or the scene is missing/failed, so the truthful-placeholder
  card renders
- **THEN** the placeholder card's rendered bounding box does not intersect the action dock's rendered
  bounding box at either 1440x900 or 1280x720

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the dock
- **THEN** each one's rendered bounding box stays above the action dock's top edge and above the command
  line, at both 1440x900 and 1280x720
