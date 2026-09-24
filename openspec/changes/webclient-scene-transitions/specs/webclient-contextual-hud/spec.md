## MODIFIED Requirements

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
The HUD SHALL show the vitals island — the vitals rows together with the conditions island beneath
them — only while at least one of these holds for the committed state: the committed mode is
`combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp)
carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries at least one
entry whose `severity` is `warning`, `harmful`, or `critical`. A condition whose `severity` is
`beneficial` or `informational` — including a passive `skill_owned` combat-modifier row — SHALL NOT
by itself make the island visible, and neither SHALL an entry with a missing or unknown `severity`.
While the island is visible its condition chips SHALL render every committed condition, whatever its
severity. Otherwise the island SHALL be hidden: from the moment the committed revision turns the rule false it
SHALL leave the accessibility tree, the tab order, and pointer hit-testing, and once its exit transition
has finished it SHALL be `display:none` and contribute no visible box. The island SHALL enter and leave
with a fade and a 12px slide at the client's motion level (`webclient-contextual-hud` "Location,
appearance, and vitals changes transition at the motion level"); at `off` it is shown and hidden in the
same frame as the commit. The rule SHALL be derived client-side from the committed
`status` panel and the committed mode alone: no server field, request, or timer is involved, and a
vital that is absent from the payload or carries a non-numeric field SHALL NOT count as below its
maximum. Dialogue mode SHALL follow the same rule as exploration; creation mode hides the island
through the visibility matrix; an unavailable `status` panel renders no vitals island at all.

While hidden, the island SHALL keep its trailing-bar memory, so the first committed revision that
lowers a vital from full shows the island with the trailing bar lagging from the previously committed
ratio exactly as an always-visible island would. When a committed revision turns the rule false while
focus is inside the island, focus SHALL move to the action dock before the island is hidden, through
the same focus-restore path a mode change uses.

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals island is absent from the accessibility tree and the tab order, and once any exit transition has finished it is hidden with `display:none` and no vitals, numerals, or low-HP marker are visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration mode carries `mp` at 40 of 60 with no condition
- **THEN** the vitals island renders with every vital's icon, label, and `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** a committed revision in exploration mode carries full vitals and one condition whose `severity` is `harmful`
- **THEN** the vitals island renders with its vitals rows and the condition chip

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** a committed revision in exploration mode carries full vitals and only conditions whose `severity` is `beneficial`, such as a passive `skill_owned` combat-modifier row
- **THEN** the vitals island stays hidden with `display:none` and none of its condition chips is visible or focusable, and no enter transition plays

#### Scenario: Visible island renders every condition chip
- **WHEN** the vitals island is visible because a vital is below its maximum and the committed conditions carry one `beneficial` and one `informational` entry
- **THEN** the island renders both condition chips

#### Scenario: Combat always shows the island
- **WHEN** the committed mode is combat with every vital full and no condition
- **THEN** the vitals island renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the island is hidden at full health and the next committed revision in the same epoch lowers `hp`
- **THEN** the island renders, the hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is on a `harmful` condition chip outside combat with every vital full, and a committed revision clears that condition, leaving only `beneficial` conditions
- **THEN** focus moves to the action dock before the island is hidden, and no focus is lost to the document body

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines, and SHALL NOT
present earlier responses: they remain readable in the full-log surface. The one exception is the clear
transition: when a new response replaces the previous one, the previous page MAY remain only as an
opaque layer over the new page that fades out within the clear duration of the client's motion level
(at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility
tree and pointer hit-testing from the moment the new response starts. Page text SHALL be set in the
serif reading face at 28px at the 1920x1080 reference size and the default prose scale, SHALL scale
with the viewport height and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line in every mode, including the whole-band width of dialogue mode.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing. When rendered, it SHALL read `▼` while the current response has further pages and
`■` on its last page. It SHALL be decorative (hidden from assistive technology), and it SHALL blink
only through the client's motion tokens, so reduced motion stops the blink. An oversize page SHALL
scroll inside the window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no unread indicator and no jump-to-latest control, and no head row
other than the dialogue name plate. In creation mode the window, its marker, and the `日誌` control are
hidden with the message region.

While the committed mode is `dialogue` and the committed `dialogue` panel is available, the window SHALL
carry a name plate above its text area, naming the host with the panel's `display_name` plus
` · 羈絆 <stage>` only when `bond_stage` is non-null; the window's text area below the plate SHALL
present the current response's pages — the session line as the narrative delivered it, paged and typed
like any response, with no separate reply box, no rows, no avatar, and no text removed or rewritten
from the narrative lines. The window SHALL carry no choice, free-dialogue, or exit row: those are the
dialogue choice list's. While mode is `dialogue` but the panel is unavailable (the transient window
between a clear seam and its commit), the window SHALL render no name plate. The window SHALL make known
to the shell, from its own reader state and never from narrative prose, whether the current response's
last page is on screen, fully shown, with no pending action mark — the moment the dialogue choice list
waits for.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters in either mode

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages, page 1 types to its end, and the player advances
  once and page 2 types to its end
- **THEN** no marker renders while either page is typing, the marker reads `▼` once page 1 is fully
  shown and `■` once page 2 is fully shown, and it is absent from the accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

#### Scenario: The dialogue line is paged under the name plate
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1920x1080
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 · 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode `dialogue` commits with `bond_stage` `null`
- **THEN** the name plate reads the host's `display_name` alone and carries no `羈絆` text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

## ADDED Requirements

### Requirement: Location, appearance, and vitals changes transition at the motion level
The stage SHALL animate the following committed changes, taking every duration and distance from the
client's motion tokens, so they follow the effective motion level of "The motion level is a client-local
preference that governs every client animation":
- **A new scene image** SHALL crossfade from the previous image to the new one over the scene duration
  (500ms at `full`). The new image SHALL start its fade only once it is decoded. Until then, the previous
  image SHALL stay visible with the dimmed treatment the backdrop already uses for a prior image, so the
  fade never passes through an empty frame and a previous scene is never presented undimmed as the
  current one. The scene label, the alternative text, and the placeholder SHALL update at commit.
- **A new location label** SHALL slide the place card's heading in from the left and fade it in, while
  the previous heading fades out. A change of the world time alone SHALL NOT animate.
- **A new current map node** SHALL pan the minimap: the drawing SHALL start where the previous current
  node stood on screen and ease to its committed placement. When the previous current node is absent
  from the new placement, the minimap SHALL show the new placement at once. The full-map surface SHALL
  NOT pan.
- **A new response** SHALL clear the message window as "The message window presents the current
  response one page at a time in the band's message region" allows: the previous page fades out over
  the clear duration (150ms at `full` and at `reduced`) while the new page starts at once.
- **A new portrait source** on a stage actor (a new image URL, or a switch between an image and a
  placeholder) SHALL crossfade over the portrait duration (400ms at `full`), and a change of the speaking
  state SHALL ease the dim.
- **The vitals island** SHALL fade in and slide 12px into place when it becomes visible, and SHALL fade
  out and slide away when it hides.

At `reduced`, each of these SHALL play as an opacity fade of at most 150ms with no slide and no pan, and
the dim SHALL change instantly. At `off`, each SHALL render its final state in the commit's frame. No
transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation
timing never gates committed state or input" requires.

#### Scenario: A new scene crossfades once decoded
- **WHEN** the effective level is `full`, the backdrop shows a done scene, and a committed revision names
  a different done scene URL
- **THEN** the scene label and alternative text read the new values in the commit's frame, the previous
  image stays visible and dimmed until the new image is decoded, and then both images are present while
  the previous one fades out over 500ms, after which only the new image remains

#### Scenario: The place card slides in the new location
- **WHEN** the effective level is `full` and a move commits a new location label, and later only the
  world time changes
- **THEN** the new heading enters from the left with a fade while the old heading fades out, and the
  time-only change swaps the time line with no transition

#### Scenario: The minimap pans to the new node
- **WHEN** the effective level is `full` and a move commits a current node adjacent to the previous one
- **THEN** the minimap's drawing starts offset so the previous current node sits where it stood, and it
  eases to the committed placement over the base duration, while the node markers and accessible names
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
- **THEN** the island fades in while sliding 12px into place, and on restore it fades out while sliding
  away and ends hidden with `display:none`

#### Scenario: Reduced plays short fades with no travel
- **WHEN** the effective level is `reduced` and a move commits a new scene, location, and current node
- **THEN** the backdrop and the place card fade within 150ms with no slide, the minimap shows the new
  placement at once, and the message window's clear fades within 150ms

#### Scenario: Off renders every final state at once
- **WHEN** the effective level is `off` and a move commits a new scene, location, current node, portrait,
  and vitals state
- **THEN** in the commit's frame the backdrop holds only the new image once decoded, and the place card,
  the minimap, the message window, the stage actor, and the vitals island each hold only their final
  state

### Requirement: A leaving element is out of reach while it animates out
Every stage element that animates out — a crossfading image or portrait, a previous place-card heading,
the message window's clearing layer, the vitals island, and every later leaving element the client
animates — SHALL leave the accessibility tree, the tab order, and pointer hit-testing at the moment the
change that removes it commits, and SHALL stay out of reach until it is removed or re-enters. Focus SHALL
never move onto a leaving element. When focus is inside an element that is about to leave, the client
SHALL move focus to its current focus home before the element leaves, so focus never falls to the
document body. An element that is entering MAY receive focus from its first frame. An element that
re-enters while it is still leaving SHALL be in reach again from that moment.

#### Scenario: A leaving layer cannot be reached
- **WHEN** the effective level is `full` and a scene crossfade, a place-card change, or a message clear
  is in progress
- **THEN** each leaving copy is inert, is absent from the accessibility tree, and receives no click, and
  sequential focus navigation never lands in it

#### Scenario: Focus leaves the vitals island before it animates out
- **WHEN** focus is on a condition chip and a committed revision hides the vitals island
- **THEN** focus has moved to the focus home before the island becomes inert, and at no point during its
  exit is focus on the island or on the document body

#### Scenario: A re-shown island is in reach again at once
- **WHEN** the vitals island starts to leave and a committed revision shows it again before its exit
  finishes
- **THEN** the island is no longer inert from that revision on, and its condition chips are focusable
