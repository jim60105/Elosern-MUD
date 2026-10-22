# Spec Delta

## MODIFIED Requirements

### Requirement: Location, appearance, and vitals changes transition at the motion level
The stage SHALL animate the committed changes below, taking every duration and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation". No transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation timing never gates committed state or input" requires.

#### Scenario: A new scene image crossfades above the previous one
- **WHEN** a same-scene replacement successfully decodes at eligible priority
- **THEN** the renderer crossfades within existing motion tokens; a different scene never retains the old place while waiting and starts with its own background at commit

#### Scenario: A new location label slides in
- **WHEN** a new location label commits, and when the world time alone changes
- **THEN** the place card's heading slides in from the left and fades in while the previous heading fades out, and a world-time-only change does not animate

#### Scenario: A new current node pans the minimap
- **WHEN** a new current node commits on a coordinate-bearing island
- **THEN** unchanged projection level/mode uses the existing pan with dots moving with the ground; changed level/mode uses a short crossfade only at effective full motion and switches immediately at reduced/off. An absent previous node retains the existing immediate no-shared-frame behavior, coordinate-free graph pan is unchanged, and the full-map surface does not pan.

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
- **WHEN** a transition above plays at reduced or off
- **THEN** the existing reduced opacity limit of 150ms with no slide/pan/marker travel and immediate dim remains; coordinate-bearing island scale or mode changes switch immediately even at reduced. At off every transition renders its final state in the commit frame; coordinate-free graph behavior remains unchanged.

#### Scenario: A new scene crossfades once decoded
- **WHEN** a different logical scene commits while its preferred image is delayed
- **THEN** prior-place image is immediately invalidated, the new scene own provisional background appears, and its decoded preferred image may fade in over that background

#### Scenario: The place card slides in the new location
- **WHEN** the effective level is `full` and a move commits a new location label, and later only the
  world time changes
- **THEN** the new heading enters from the left with a fade while the old heading fades out, and the
  time-only change swaps the time line with no transition

#### Scenario: The minimap pans to the new node
- **WHEN** effective motion is full and an adjacent move commits with unchanged coordinate-bearing island level and mode
- **THEN** the drawing starts offset to preserve the previous current node screen position and eases over the existing base duration, including the world-anchored dots; the current marker travels the existing step and committed visibility, names and click targets already describe the new placement. A changed level or mode instead uses the approved short crossfade, with no equal-scale FLIP.

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
