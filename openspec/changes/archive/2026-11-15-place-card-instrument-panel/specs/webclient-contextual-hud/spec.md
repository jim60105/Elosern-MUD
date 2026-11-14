## ADDED Requirements

### Requirement: An instrument panel wears a feathered ground and one brass fitting instead of a box
A HUD surface that its own requirement names an instrument panel SHALL have no border, corner radius, box shadow or opaque fill of its own. Beneath its content it SHALL paint a blurred ink ground that feathers out toward its open sides and one brass fitting along its anchored edges, both decoration outside the accessibility tree and pointer hit-testing, and its content SHALL stay clear of the fitting's spine.

#### Scenario: The panel itself is not a box
- **WHEN** an instrument panel renders in the live client
- **THEN** its own computed border widths are 0, its corner radius is 0, its box shadow is `none` and its background colour is transparent

#### Scenario: The ground and the fitting are painted decoration
- **WHEN** an instrument panel in the `map` column renders
- **THEN** a layer beneath its content paints the shared panel ink with a backdrop blur and a mask that keeps it solid at the right edge and fades it toward the left edge and over the bottom edge, and a second layer paints the band ornament at the top-right corner with a crown along the top and a spine down the right side; neither layer is an element in the accessibility tree and neither receives pointer events

#### Scenario: Content never crosses the spine
- **WHEN** an instrument panel in the `map` column renders its content at 1280x720, 1451x790 and 2560x1440
- **THEN** every content element's right edge stands at least 14px × S left of the panel's right edge, which is where the spine runs

#### Scenario: One token change reaches every panel
- **WHEN** the shared panel ink, the band ornament or the band edge tokens change
- **THEN** every instrument panel's ground and fitting change with them, because each panel resolves them from the shared design tokens rather than from per-component literals

## MODIFIED Requirements

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's top-right corner directly below the top band and directly above the minimap island, while the committed mode is exploration, and SHALL NOT render it in combat, creation or settled dialogue mode. The card SHALL state the current location as its heading and the world date/time beneath it, and SHALL be the only surface on the stage or in the top band that states either value.

#### Scenario: Dialogue entry leaves only inert exit paint
- **WHEN** the mode live-enters dialogue
- **THEN** the card MAY retain only the inert exit paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility tree and tab order from commit, and becomes `display:none` when the anchor's fade ends

#### Scenario: The card carries the room actions at the exploration root
- **WHEN** the committed mode is exploration while the exploration panel is available and the exploration dock is at its root frame
- **THEN** the card also carries the room actions `webclient-room-actions` defines — a 查看房間 icon button beside the heading and a 休息 button beside the time — and in every other mode and state it carries no control

#### Scenario: The location resolves in a fixed order
- **WHEN** the card resolves its location
- **THEN** it uses the best server-authored place name the client already holds: the committed `local_map` panel's `current_node` label when that panel is available, names a current node, that node is present in the panel's nodes, and its label is a non-empty string; otherwise the committed status panel's actor location label; otherwise the card's own unavailable placeholder `位置：--`

#### Scenario: The world time is committed or placeholdered
- **WHEN** the card renders its world date/time
- **THEN** it is the committed world-time label, and the card's own unavailable placeholder `時間：--` when none is committed

#### Scenario: The card composes and guesses nothing
- **WHEN** location candidates exist or identifiers are available
- **THEN** the card composes no third string from the two location candidates, derives no name from any node or room identifier, renders no raw room key while a committed panel carries the authored place name for the same room, and renders no raw mode label in place of the location

#### Scenario: The card wears island chrome at a fixed size
- **WHEN** the card renders
- **THEN** it is an instrument panel as "An instrument panel wears a feathered ground and one brass fitting instead of a box" defines (no border, radius, shadow or opaque fill of its own), spans the full width of the `map` column, keeps a fixed height whatever the label lengths, and truncates a label that exceeds its width with an overflow indicator while keeping the full label as its accessible text

#### Scenario: The card is display-only
- **WHEN** the card renders outside exploration, or while the exploration panel is unavailable
- **THEN** it carries no control, no tab stop, and no dispatch; in exploration with the panel available its only controls are the 查看房間 and 休息 buttons, which never truncate the heading's accessible name, and the card itself dispatches nothing

#### Scenario: The two values read on two levels
- **WHEN** the card renders heading and time
- **THEN** it sets them on two levels: the location heading in the serif face at the `--text-lg` step, then a quiet decorative gold rule, hidden from assistive technology, then the world-time line; the heading, the rule, and the time line fit the card's fixed height; the heading and the time line align their text to the right, toward the panel's spine, and the rule stands at the right end of the card's content box, whether or not the room actions render

#### Scenario: The time line keeps every server value intact
- **WHEN** the world-time line renders
- **THEN** it carries no leading separator glyph or rule before its first value, uses the numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 16px chrome floor), and renders the committed world-time label (or its placeholder) verbatim, with every date and time value intact: all time values remain server-authored, and the card reformats, abbreviates, or derives none of them

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 ‧ 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 ‧ 12:00`, and no other stage or top-band element states either string

#### Scenario: The card heads the map column
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the place card is the first island of the `map` anchor, its rendered width equals the `map` anchor's width (±1px), and the stage renders no place card in its left column

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation, and later dialogue
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode and in settled dialogue mode the place card is not rendered and holds no tab stop; during live dialogue entry only its inert exit paint may remain until the map anchor's fade ends

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the heading is set one
  step below the display size the stage's island chrome uses at `--text-lg`, the time line's numerals
  are tabular lining figures in the numeral face, and the card keeps its fixed height

#### Scenario: The place card carries its amendment
- **WHEN** the `place-card-relocation` amendment applies to this requirement
- **THEN** the visible-mode set narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells

#### Scenario: The card is absent in combat
- **WHEN** the committed mode changes from exploration to combat, and later back
- **THEN** in combat the place card is not rendered (`display:none`, outside the accessibility tree) while it keeps its committed location and time, and on the return it renders again as the first island of the `map` anchor

#### Scenario: The room actions wear no chrome
- **WHEN** the card carries its room actions
- **THEN** the 查看房間 and 休息 buttons have no border and no background fill of their own, each keeps a hit box at least 30px × S tall and wide, the 休息 button keeps its visible word beside its icon, and only the hovered or keyboard-focused button shows the active brass tick beneath it while every other button shows none

#### Scenario: The room actions stand clear of the spine
- **WHEN** the card carries its room actions at 1280x720, 1451x790 and 2560x1440
- **THEN** each button's right edge stands at least 14px × S left of the card's right edge, and the heading's accessible name is still never truncated by the buttons

### Requirement: Location, appearance, and vitals changes transition at the motion level
The stage SHALL animate the committed changes below, taking every duration and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation". No transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation timing never gates committed state or input" requires.

#### Scenario: A new scene image crossfades above the previous one
- **WHEN** a same-scene replacement successfully decodes at eligible priority
- **THEN** the renderer crossfades within existing motion tokens; a different scene never retains the old place while waiting and starts with its own background at commit

#### Scenario: A new location label slides in
- **WHEN** a new location label commits, and when the world time alone changes
- **THEN** the place card's heading slides in from the right, the column's anchored edge, and fades in while the previous heading fades out, and a world-time-only change does not animate

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
- **THEN** the new heading enters from the right with a fade (its horizontal offset is positive while it
  travels) while the old heading fades out, and the time-only change swaps the time line with no transition

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
