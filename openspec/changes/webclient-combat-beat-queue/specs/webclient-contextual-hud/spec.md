## MODIFIED Requirements

### Requirement: Presentation timing never gates committed state or input
The client SHALL apply every committed change to its state and to the document immediately; motion
SHALL only decide how the view moves between two committed states. A transition SHALL NOT delay a
committed value, a mode or visibility attribute, the accessibility tree, or the tab order beyond the
moment the change commits, and SHALL NOT delay the player's ability to act beyond its own duration at
the current motion level. A transition interrupted by a newer committed change SHALL run toward the
newer state, and SHALL NOT first finish the older one.

Presentation that plays in steps — message pages, and a combat round's beats as `webclient-combat-menu`
"A combat round plays beat by beat" defines — SHALL follow three rules. Steps play in the order their
data committed, and a step never reorders, drops, or alters committed data. A player click or press that
advances the presentation shows the current step's end state at once; for a playing combat round it
shows the whole round's end state. A new player action shows every queued step's end state, a playing
combat round's included, before its own response starts. Nothing is lost: every stepped text stays in
the full log. Any pause a stepped presentation waits for SHALL come from the motion tokens, read by the
client's script from the same tokens the styles use, and SHALL resolve to zero at `off`; revealing text
follows the reader's text speed. The one presentation that holds the player's input is a playing combat
round: it keeps the command panel locked until it ends, and the player can end it at once with a click
or press on the message window or a typed command.

#### Scenario: A mode change commits before its transition ends
- **WHEN** the effective level is `full` and a committed revision changes the mode
- **THEN** the stage's mode attribute, the committed surfaces' accessibility state, and the store's
  view carry the new mode in the same frame as the commit, before any transition finishes

#### Scenario: Input is available within the transition's duration
- **WHEN** the effective level is `full` and the player opens a drawer or a new response starts
- **THEN** the drawer takes focus and the message window accepts Enter at once, without waiting for
  a transition to finish

#### Scenario: A combat round holds the panel only until the player ends it
- **WHEN** the effective level is `full`, a combat round is playing, and the player clicks the message
  window
- **THEN** the command panel accepts activation again as soon as the declared revision is also
  accepted, and every displayed value is the committed value

#### Scenario: A click shows the step's end state and a new action flushes
- **WHEN** a page is typing and the player clicks the message window, and later acts while unread
  pages remain
- **THEN** the click shows the page in full at once, and the action shows the previous response's
  last page complete before the new response's first page starts, with every page still in the full
  log

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines — or, while the
current response carries a combat round the client presents, as that round's beat pages followed by the
response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and
SHALL NOT present earlier responses: they remain readable in the full-log surface. The one exception is the clear
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
the page is typing and while a combat round plays by itself. When rendered, it SHALL read `▼` while the current response has further pages and
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

### Requirement: Vitals pair an icon, a label, and numerals with a trailing damage bar
Each of hp, mp, and sp SHALL render as one vital row carrying an icon, a Traditional Chinese label,
and the `current / maximum` numerals from `status.resources` — or, for hp while a combat round plays,
the displayed value that `webclient-combat-menu` "A combat round plays beat by beat" defines — above a track containing a trailing bar
and a fill. The numerals SHALL render at every value, so no vital state is conveyed by the coloured
fill alone. The sp fill SHALL carry a non-colour texture distinguishing it from the hp and mp fills.

The trailing bar SHALL exist to make damage taken visible: it SHALL lag the fill when the ratio falls
and SHALL be overtaken by the fill when the ratio rises. It SHALL be decorative — hidden from the
accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already
carry on the same revision. It SHALL NOT render any value that was not a previously displayed ratio of
that same gauge, where a displayed ratio comes only from the committed `status` or from a committed
beat's `hp_after` during a round's playback, SHALL NOT be interpolated or extrapolated from narrative text or an action result,
and SHALL reset to the current ratio when the epoch changes, so no trail is drawn across a reconnect.
Its motion SHALL be token-gated so the reduced-motion block disables it.

A vital at or below the client's display threshold SHALL be marked by both a recolour and an explicit
text marker, never by the recolour alone.

#### Scenario: Each vital is legible without colour
- **WHEN** the vitals island renders with the `status` panel committed
- **THEN** each of hp, mp, and sp shows an icon, a text label, and its `current / maximum` numerals, and the sp fill is distinguishable from hp and mp by texture rather than by hue

#### Scenario: Damage leaves a visible trailing bar
- **WHEN** a committed revision lowers a gauge's ratio
- **THEN** the fill moves to the new ratio and the trailing bar follows behind it, so the gap between them shows the amount lost, and the numerals show the new value immediately

#### Scenario: Healing shows no trailing bar
- **WHEN** a committed revision raises a gauge's ratio
- **THEN** the fill overtakes the trailing bar and no lagging gap is drawn

#### Scenario: The trailing bar follows a round's displayed hit points
- **WHEN** a playing combat round shows the player's hp stepping from 40 to 28 and then to 15 of 60
- **THEN** the numerals and the fill show each displayed value in turn, the trailing bar lags each drop
  from the previously displayed ratio, and once the round ends the numerals and fill show the committed
  value

#### Scenario: The trailing bar never shows an uncommitted value
- **WHEN** the trailing bar renders at any point
- **THEN** its width corresponds to a ratio that was previously displayed for that same gauge — a committed `status` value, or a committed `combat_beats` beat's `hp_after` during that round's playback — never a value from neither source, and it is absent from the accessibility tree

#### Scenario: A reconnect does not draw a trail across epochs
- **WHEN** a new epoch's snapshot commits after a reconnect
- **THEN** the trailing bar resets to the current ratio and no gap is drawn between the pre-reconnect and post-reconnect values

#### Scenario: A low vital is marked by text as well as colour
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** the row carries both the low recolour and an explicit text marker, and the numerals continue to render

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map`
anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the
player's side and the opposing side using the committed participants' server-authored team values, in
the presenter's order. Each participant SHALL render its session token, its display name, its current
and maximum hit points as numerals — the current value being, while a combat round plays, the displayed
value that `webclient-combat-menu` "A combat round plays beat by beat" defines — and its state; a non-active state SHALL be conveyed by an explicit
text marker in addition to any colour. The frame SHALL NOT invent a field the participant descriptor
does not carry. The frame SHALL list every participant of both sides, including the foes the foe line-up
does not stand on the stage, and it SHALL remain the only surface that states participant tokens, hit
points, and states: the foe line-up in `actor-right` carries decorative portraits only.

Each participant's portrait SHALL be resolved only by looking its server-authored portrait reference
up in the committed art panel's portrait catalog: a resolvable entry SHALL render that entry, an
entry that resolves to a placeholder SHALL render the placeholder card, and a null reference or an
unavailable art panel SHALL render no portrait at all. The client SHALL NOT construct a portrait
subject key or URL. While the participant frame is mounted, the frame and the stage actors SHALL be the
only presenters of the portrait catalog, so no separate portrait strip is rendered alongside them.

The participant frame SHALL be display-only: it SHALL NOT be a row container, SHALL NOT be part of
the dock's composite widget, and SHALL NOT be a second tab stop. Target selection happens in the
dock's target frame.

#### Scenario: Both sides render from the payload
- **WHEN** a combat session commits participants on both teams
- **THEN** the frame renders the player's side and the opposing side in presenter order, each participant showing its token, display name, current and maximum hit points, and state

#### Scenario: A non-active participant is marked in text
- **WHEN** a participant's state is fled, knocked out or defeated
- **THEN** the frame renders an explicit text marker for that state alongside any colour treatment

#### Scenario: A portrait comes only from the catalog
- **WHEN** a participant carries a portrait reference present in the committed portrait catalog
- **THEN** the frame renders that catalog entry, and when the reference is null or the art panel is unavailable it renders no portrait and constructs no URL

#### Scenario: The frame does not compete for focus
- **WHEN** the participant frame is mounted during combat
- **THEN** it is not reachable by sequential keyboard navigation, the dock's active row container remains the surface's only listbox, and no portrait strip is rendered outside the frame and the stage actors

#### Scenario: The frame sits in the map anchor, not on a portrait anchor
- **WHEN** a combat session commits participants at 1440x900 and 1280x720
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds only the foe line-up's stage actors and no frame row, token, or hit-point numeral, and the frame's visible box intersects neither the bottom band nor the command line
