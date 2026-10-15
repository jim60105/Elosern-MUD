# Spec Delta

## MODIFIED Requirements

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The backdrop SHALL consume canonical scene load state and same-scene retention, displaying the successful source or that new scene's own provisional bundled/terminal art. Reached failures SHALL remain locally accessible after fallback. Mode changes SHALL not select art. Existing caption placement, focus and non-overlap invariants SHALL remain; CSS sample backgrounds SHALL be removed.

#### Scenario: The backdrop never lies about the scene
- **WHEN** any scene renders on the backdrop
- **THEN** the backdrop presents no invented image as authoritative and no stale image as current

#### Scenario: A bundled sample is captioned inside one status badge
- **WHEN** expected missing/pending generation reaches bundled scene art
- **THEN** it is official type artwork with factual generation explanation if needed, no sample-only label or error styling; no CSS sample wash remains

#### Scenario: Portrait samples stay labelled and subordinate
- **WHEN** a figure lacks real art
- **THEN** its canonical alpha terminal and truthful identity appear; no decorative sample is attributed to the subject

#### Scenario: The combat hold never holds scene identity
- **WHEN** held combat decoration spans a new logical scene commit
- **THEN** the previous-place background is invalidated immediately; current scene type determines its own provisional/resolved image while combat decoration remains presentation-only

#### Scenario: All required labels exist as text outside the bitmap
- **WHEN** scene art displays
- **THEN** label, nonduplicate alternative text, factual progress and accessible failure explanation remain DOM text outside the bitmap; exhausted non-image styling may retain existing mode tokens without using mode to select any image

#### Scenario: Backdrop captions never meet the band or dock
- **WHEN** the backdrop's own floating caption elements — the status badge, the `目前場景圖片生成中` pending notice, the scene label and alternative-text captions, and the full-view control — render at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** none of them overlaps the bottom band's, the action dock's, or the command line's rendered content, extending the sibling stage requirement's general anchor non-overlap invariant to these backdrop-internal captions, which sit outside the named stage anchors but are absolutely positioned within the same full-bleed stage

#### Scenario: The caption row stands only for a real scene image
- **WHEN** generated, operator or bundled official scene art is on screen
- **THEN** its caption/fullview control use the successful resource even when generation is missing/pending/failed, without duplicate alternative text

#### Scenario: The caption row sits centred on the stage's lower edge
- **WHEN** the scene label, the alternative text, the pending notice, and the full-view control render, with or without the foe line-up standing in combat
- **THEN** they render as one caption row on the stage box's lower edge, standing just above the command-line row docked on the band's top edge, centred in the open stage between the `actor-left` and `actor-right` anchor boxes — or, while the foe line-up stands in combat, between the `actor-left` anchor box and the line-up's leftmost foe, until a leaving line-up has faded — so no portrait anchor (which paints above the backdrop), no foe, and no other HUD surface covers any part of it in any mode

#### Scenario: The caption row stays one line tall
- **WHEN** the row is too narrow for both the alternative text and the label, or a label or alternative text is longer than the row
- **THEN** the alternative text gives way before the scene label, the long text ends in an ellipsis on screen while its full text stays in the DOM, the row stays one line tall, and the dialogue choice list stops above the row

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped to the stage box behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

#### Scenario: A missing scene degrades to the mode gradient
- **WHEN** generation has no image
- **THEN** required type art is attempted with no error for expected absence; only exhausted permitted image sources use non-image background

#### Scenario: A degraded scene shows one status badge and no caption row
- **WHEN** all permitted scene resources fail
- **THEN** one local failure explanation appears without a broken image or broken-only fullview; healthy official fallback keeps its normal caption/fullview affordance

#### Scenario: An alternative text equal to the label is not repeated
- **WHEN** a `done` scene's alternative text is identical to its label
- **THEN** the caption row renders the label once and no alternative-text element

#### Scenario: An unavailable art panel is indistinguishable from an ungenerated scene
- **WHEN** the art panel cannot provide image data
- **THEN** safe same-identity last-known content or permitted fallback remains with a local availability indication distinct from expected missing generation

#### Scenario: A pending scene keeps its prior image labelled
- **WHEN** the same scene/generation subject is pending and has applicable retained success
- **THEN** its good image is retained with factual progress, never across a different place

#### Scenario: The combat stage is visually distinct
- **WHEN** combat begins in the same logical scene
- **THEN** the artwork source is unchanged; existing non-image styling and gameplay decoration may differ without selecting different sample images

#### Scenario: The truthful-placeholder caption never intrudes on the action dock
- **WHEN** the `art` panel is unavailable or the scene is missing/failed, so the status badge
  renders
- **THEN** the status badge's rendered bounding box intersects neither the bottom band's nor the
  command line's rendered bounding box at 1451x790 or at any larger viewport up to the chrome cap

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1451x790 and at every larger viewport up to the chrome cap

#### Scenario: The scene caption stands on the stage floor between the portraits
- **WHEN** the scene label, alternative text, and full-view control render with the command line expanded
  at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** their caption row's bottom edge lies at most 16px above the command-line row's top edge, the
  row is horizontally centred between the `actor-left` and `actor-right` anchor boxes (±1.5px), and each
  part lies between those boxes with no other surface painted over it

#### Scenario: The scene caption clears the foe line-up
- **WHEN** a combat snapshot commits one, two, and three active foes with the command line expanded at
  1451x790 and at every larger viewport up to the chrome cap
- **THEN** the caption row lies between the `actor-left` anchor box and the leftmost foe's box, horizontally
  centred between them (±1.5px), with no foe painted over any of its parts

### Requirement: Location, appearance, and vitals changes transition at the motion level
The stage SHALL animate the committed changes below, taking every duration and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation". No transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation timing never gates committed state or input" requires.

#### Scenario: A new scene image crossfades above the previous one
- **WHEN** a same-scene replacement successfully decodes at eligible priority
- **THEN** the renderer crossfades within existing motion tokens; a different scene never retains the old place while waiting and starts with its own background at commit

#### Scenario: A new location label slides in
- **WHEN** a new location label commits, and when the world time alone changes
- **THEN** the place card's heading slides in from the left and fades in while the previous heading fades out, and a world-time-only change does not animate

#### Scenario: A new current node pans the minimap
- **WHEN** a new current map node commits, and when the previous current node is absent from the new placement
- **THEN** the minimap pans: the drawing starts where the previous current node stood on screen and eases to its committed placement, and the current-node marker travels the step from the node the player left to the new current node, so a move reads even when the drawing itself does not shift; an absent previous node shows the new placement at once; and the full-map surface does not pan

#### Scenario: A new response clears the message window
- **WHEN** a new response commits
- **THEN** the message window clears as "The message window presents the current response one page at a time in the band's message region" allows: the previous page fades out over the clear duration (150ms at `full` and at `reduced`) while the new page starts at once and surfaces beneath it within the same duration, so the two pages never read through each other

#### Scenario: A new portrait source crossfades
- **WHEN** a stage actor's portrait source changes (a new image URL, or a switch between an image and a placeholder), or the speaking state changes
- **THEN** the source crossfades over the portrait duration (400ms at `full`), and the speaking change eases the dim

#### Scenario: The vitals dock rises and sinks
- **WHEN** the vitals dock — the condition icon row and the vitals bars as one surface — shows or hides
- **THEN** it fades in while rising 12px into its bottom-anchored resting position (entering from 12px below it, so it reads as rising out of the band's edge), and fades out while sinking 12px back toward the band when it hides

#### Scenario: Reduced and off compress every transition
- **WHEN** any transition above plays at `reduced`, and at `off`
- **THEN** at `reduced` it plays as an opacity fade of at most 150ms with no slide, no pan, and no marker travel, and the dim changes instantly; at `off` it renders its final state in the commit's frame

#### Scenario: A new scene crossfades once decoded
- **WHEN** a different logical scene commits while its preferred image is delayed
- **THEN** prior-place image is immediately invalidated, the new scene own provisional background appears, and its decoded preferred image may fade in over that background

#### Scenario: The place card slides in the new location
- **WHEN** the effective level is `full` and a move commits a new location label, and later only the
  world time changes
- **THEN** the new heading enters from the left with a fade while the old heading fades out, and the
  time-only change swaps the time line with no transition

#### Scenario: The minimap pans to the new node
- **WHEN** the effective level is `full` and a move commits a current node adjacent to the previous one
- **THEN** the minimap's drawing starts offset so the previous current node sits where it stood, and it
  eases to the committed placement over the base duration while the current-node marker travels from
  the node the player left, and the nodes' visibility states, accessible names, and click targets
  already describe the new placement

#### Scenario: The message window clears between responses
- **WHEN** the effective level is `full`, page 1 of a response is on screen, and the player acts
- **THEN** the new response's first page starts typing at once beneath an inert layer holding the
  previous page, which fades out over 150ms and is then removed

#### Scenario: An appearance change crossfades the player's portrait
- **WHEN** the effective level is `full` and the roster's current character portrait changes URL
- **THEN** the player's stage actor shows both portraits while the previous one fades out over 400ms, and
  then only the new one

#### Scenario: The vitals island fades and slides in and out
- **WHEN** the effective level is `full` and a committed revision lowers `hp` from full outside combat,
  and a later revision restores it
- **THEN** the dock fades in while rising 12px from 12px below its resting position, and on
  restore it fades out while sinking 12px toward the band and ends hidden with `display:none`

#### Scenario: Reduced plays short fades with no travel
- **WHEN** the effective level is `reduced` and a move commits a new scene, location, and current node
- **THEN** the backdrop and the place card fade within 150ms with no slide, the minimap shows the new
  placement at once, and the message window's clear fades within 150ms

#### Scenario: Off renders every final state at once
- **WHEN** motion is off and scene/location/portrait/vitals commit
- **THEN** each canonical value updates in the commit frame; the new scene displays its own available background while preferred pixels decode and never holds the old place

