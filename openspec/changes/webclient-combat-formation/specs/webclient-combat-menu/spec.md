## MODIFIED Requirements

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL preserve the root inventory of the client
combat-menu resolver (the root list of `web/static/webclient/js/elosern/combat_menu.js`:
Attack, Skills, Items, the client-local Bag drawer opener, Defend, Flee, and the
confirmed Forfeit entry) and their existing availability/order. No new root action SHALL
be introduced. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop
one level, and disabled entries SHALL send no packet.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.cast` for `basic_attack` exactly once and the ordinary combat-session path resolves the result

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the player focuses Items or Defend and presses Enter
- **THEN** its `not_implemented` explanation remains readable and no `ui_action` message is emitted

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the Forfeit entry but has not confirmed
- **THEN** no mutation is sent, and Escape returns exactly one menu level without ending combat

#### Scenario: Skills opens a bounded master-detail
- **WHEN** the player opens Skills in combat with skills owned across several categories
- **THEN** the dock lists one row per committed category with its label and its own descriptor count, in the panel's order, instead of one flat list of every owned skill

#### Scenario: A single-sub-group category skips the group level
- **WHEN** the player opens a category whose committed payload carries exactly one sub-group
- **THEN** the skill frame opens directly, and Escape from it returns to the category frame

#### Scenario: A multi-sub-group category presents its groups first
- **WHEN** the player opens a category whose committed payload carries more than one sub-group
- **THEN** the dock lists one row per sub-group in the panel's order, and opening one lists exactly that group's skills in the panel's order

#### Scenario: The master-detail changes no cast payload
- **WHEN** the player reaches a target through the category and group frames and confirms a cast
- **THEN** the emitted `combat.cast` payload is byte-identical to the payload the same skill, scale, and target produce without the master-detail

#### Scenario: The root list geometry matches its rendered order
- **WHEN** the player presses the arrow keys on the combat root
- **THEN** focus moves through the current resolver's root items in their rendered order with the vertical arrow keys, and the horizontal arrow keys move focus nowhere

#### Scenario: A single-target frame is a vertical list
- **WHEN** the player opens Attack with an ally and two foes listed as candidates
- **THEN** the target rows render in one column in the server's order, each marked as ally or foe, ArrowDown moves to the next candidate, and ArrowRight moves focus nowhere

#### Scenario: Categories and groups are vertical lists
- **WHEN** the player opens Skills with several categories, and later a category with several sub-groups
- **THEN** each frame renders one row per entry in a single column, ArrowDown moves to the next entry and wraps at the end, and ArrowRight moves focus nowhere

#### Scenario: The participant frame renders the committed session
- **WHEN** a combat session commits participants on both teams, one of them fled or knocked out
- **THEN** every drawn figure other than the controlled one carries its plate with display name, hit-point stroke and current and maximum hit points (the controlled figure's values stay in the vitals dock), the session token is part of the plate's accessible name only, and no plate is reachable by sequential keyboard navigation in this requirement

#### Scenario: A participant portrait comes only from the catalog
- **WHEN** a participant carries a `portrait_ref` present in the committed portrait catalog, and another carries `null`
- **THEN** the first renders that catalog entry (including its placeholder card) and the second renders no portrait, and the browser constructs no subject key or URL

#### Scenario: The forfeit confirmation is an explicit two-step panel
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, no mutation is sent, and only activating the confirm row emits one `combat.forfeit` carrying the current session identifier

#### Scenario: The forfeit warning states the consequence
- **WHEN** the forfeit confirmation screen renders
- **THEN** it is an explicit warning panel stating what forfeiting does

#### Scenario: Each root action keeps its dedicated route
- **WHEN** the player activates each entry of the preserved root inventory
- **THEN** Attack selects targets for innate `basic_attack`; Skills opens the committed
  skill categories as a bounded master-detail rather than one flat list; Items and
  Defend remain focusable but disabled with code `not_implemented`; Flee invokes the
  innate flee path; and Forfeit requires an explicit confirmation screen, retaining its
  explicit confirmation route

#### Scenario: The root is a wrapping single-column vertical list
- **WHEN** the combat root (including the recovery root) renders with more than one row
- **THEN** it renders as a single vertical icon-and-label list with one column, Up/Down
  traverse and wrap in rendered order, and Left/Right are no-ops at root

#### Scenario: The Skills row carries the committed descriptor count
- **WHEN** the root list renders the Skills row
- **THEN** it carries a neutral inline count equal to the committed descriptor count and
  omits the count at zero

#### Scenario: Deeper frames replace the root list with one active container
- **WHEN** the player opens a frame deeper than the root
- **THEN** it replaces the root list and retains one active row container

#### Scenario: Confirmation frames follow server candidate order with side markers
- **WHEN** the single-target, self, or no-target confirmation frame renders
- **THEN** it renders as the same single-column list in the server's candidate order,
  each target row marked by its side as well as its name, and the AREA frame keeps its
  token grid

#### Scenario: Root detail copy is explanatory only
- **WHEN** the detail beside a root row carries client-local explanatory copy describing
  what the command opens or does
- **THEN** it states no gameplay value, and every count it shows is derived from the
  committed descriptors

#### Scenario: The master-detail never renders uncarried fields
- **WHEN** a master-detail level renders committed entries
- **THEN** it preserves the committed panel's order exactly, does not reorder, filter,
  merge, or paginate it, and renders no badge or field the descriptor does not carry —
  in particular no out-of-combat marker, which no presenter serializes

#### Scenario: Focus stays visible in the bounded row region
- **WHEN** a frame renders or focus changes
- **THEN** the focused row is scrolled into view within the dock's bounded row region

#### Scenario: Escape pops exactly one master-detail level
- **WHEN** the player presses Escape inside the master-detail
- **THEN** exactly one of its levels pops at a time, and the subsequent scale and target
  steps are unchanged in behaviour and in payload

#### Scenario: The participant frame is display-only in the HUD island
- **WHEN** combat presents the figure plates
- **THEN** they are not a row container and not part of the dock's composite widget;
  target selection remains the dock's target frame

#### Scenario: Category frames carry per-row descriptor counts
- **WHEN** the category or group frame renders its entries
- **THEN** it renders the same single-column vertical list with each row carrying its
  own descriptor count, Up/Down move between categories or groups, and Left/Right are
  no-ops there

#### Scenario: The skill frame lists descriptors beside a detail pane
- **WHEN** the player reaches the skill frame of the master-detail
- **THEN** it lists that group's descriptors, each row carrying the skill's label and
  resource cost, beside the detail pane that names the focused skill, its description,
  its cost, its target requirement, and its server-authored reason when it is
  unavailable

#### Scenario: No level ever offers a single choice
- **WHEN** the master-detail walks the category → group → skill levels
- **THEN** a category frame lists one entry per committed category group with its label
  and its own descriptor count; a group frame is shown only when that category carries
  more than one sub-group; and a category carrying exactly one sub-group opens the
  skill frame directly, so no level ever offers a single choice

#### Scenario: Participant hit points are numerals and missing art means no portrait
- **WHEN** the figure plates render committed participants, or the art panel is
  unavailable
- **THEN** each plate shows its participant's display name and current and maximum hit
  points as numerals (its session token only in the accessible name), and a null reference
  or an unavailable art panel yields the figure's truthful placeholder with no
  client-constructed subject key or URL

### Requirement: A combat round plays beat by beat
When a committed publication carries an available `combat_beats` panel whose round the
client has not presented in the current epoch, and that publication completes the
player's own `combat.cast`, `combat.flee`, or `inventory.use` action, the client SHALL
present that round as one step per beat, in the beats' order, attached to that action's
response. A round seen in any other way, including after a reconnect, SHALL NOT be
presented as steps, and no round SHALL be presented twice.

#### Scenario: A round plays one beat per page
- **WHEN** the effective level is `full` and an accepted basic attack settles a non-terminal round with a
  `roll` beat and a `damage` beat
- **THEN** the message window types the roll beat's text as a page, then after the beat pause types the
  damage beat's text as the next page, and then shows the round's closing line as the next page

#### Scenario: Displayed hit points follow the beats and snap at the end
- **WHEN** a foe at 30 hit points takes damage beats with `hp_after` 18 and then 0 in a playing round
- **THEN** the foe's plate shows 30, then 18 after the first damage beat, then 0 after the
  second, and once the round ends it shows the committed value

#### Scenario: The command panel unlocks after playback and the revision
- **WHEN** the declared revision of a combat action is accepted while its round is still playing
- **THEN** the dock accepts no activation and sends no `ui_action` until the round has ended, and
  accepts the next activation once it has

#### Scenario: A click ends the round
- **WHEN** a round is playing its first of three beats and the player clicks the message window
- **THEN** the lock from playback clears at once, every displayed hit-point value equals the committed
  value, and the window shows the page after the beat pages

#### Scenario: A typed command ends the round
- **WHEN** a round is playing and the player sends a typed command
- **THEN** the round ends before the command's input line is appended, and the command's response is
  presented from its first page

#### Scenario: Reduced keeps the order and the pauses
- **WHEN** the effective level is `reduced` and a round with three beats plays
- **THEN** each beat page appears in full at once, each next beat follows after the 400ms beat pause,
  and the order equals the beats' order

#### Scenario: Off presents the beats as text pages
- **WHEN** the effective level is `off` and a round with two beats settles
- **THEN** the command panel unlocks as soon as the declared revision is accepted, and the reader turns
  one page per beat, each holding that beat's text, followed by the round's closing line

#### Scenario: The round that ends the fight plays its beats
- **WHEN** an accepted attack defeats the last foe and the full snapshot commits mode `exploration`
  with an available `combat_beats` panel
- **THEN** the mode, the exploration surfaces, and the store's view carry `exploration` at once, the
  round's beats are presented in order ending with the defeat beat, and the outcome lines follow them

#### Scenario: Without beats the round pages as text
- **WHEN** an accepted combat action's publication carries the unavailable `combat_beats` form
- **THEN** the round's narrative is paged as an ordinary response, the vitals move once to the committed
  values, and the dock unlocks when the declared revision is accepted

#### Scenario: A reconnect replays no round
- **WHEN** the client reconnects after a round has played, or reloads while a round is playing
- **THEN** no beat is presented again, the window shows the last page of the last response fully shown,
  and every displayed value is the committed value

#### Scenario: An unknown participant is text only
- **WHEN** a beat's target names no participant known to the client
- **THEN** its text is presented as its page and no displayed hit-point value changes for it

#### Scenario: The ending round presents like any round
- **WHEN** the completing publication has already committed mode `exploration` (the
  round that ends the fight)
- **THEN** that round SHALL be presented the same way, and its committed exploration
  state is not held back

#### Scenario: A beat is exactly its plain text as one page
- **WHEN** a playing round's beats are paged into the message window
- **THEN** each beat is one page holding exactly the beat's text as plain text, split
  over more pages only when it does not fit one

#### Scenario: Beat pages replace the round's own event lines
- **WHEN** a playing response is paged
- **THEN** the response's first lines, one per event log the beats name, are not paged
  again, every later line of the response (the round's closing line, a fight's outcome
  and aftermath) follows the beat pages as ordinary pages, and the log keeps every line
  unchanged

#### Scenario: Full and reduced motion play the round by itself
- **WHEN** the effective motion level is `full` or `reduced`
- **THEN** the round plays by itself: each beat page is revealed at the reader's text
  speed (instant below `full`); once fully shown, the beat's stage gesture plays as
  `webclient-contextual-hud` "Combat beats are choreographed on the stage at the motion
  level" defines, and the next beat follows after that gesture and the beat pause of the
  client's motion tokens (400ms at `full` and at `reduced`)

#### Scenario: Off never plays the round by itself
- **WHEN** the effective motion level is `off`
- **THEN** the round does not play by itself: its beat pages and the following pages are
  ordinary pages the reader turns, and presentation of the round ends at once

#### Scenario: Displayed hit points track damage beats in both surfaces
- **WHEN** a playing round damages a participant whose previous committed hit points are
  known
- **THEN** that participant displays its previous committed value until its first damage
  beat, and after each of its damage beats that beat's `hp_after`, in the vitals and on
  its figure plate

#### Scenario: Playback end snaps every value and nothing else follows the beats
- **WHEN** a round's presentation ends
- **THEN** every displayed value is the committed `status` and participant value, and no
  other resource, marker, or visibility rule follows the beats

#### Scenario: Playback lock stacks on the revision lock
- **WHEN** a round plays by itself while the declared-revision lock is also pending
- **THEN** the command panel stays locked under both, and unlocks when both have cleared

#### Scenario: Pointer or keyboard skip ends the round at once
- **WHEN** the pointer activates the message window, or the player presses Enter or
  Space on its page surface, during playback
- **THEN** the round ends at once: every displayed value becomes the committed value,
  the lock from playback clears, and the window shows the response's first page after
  the beat pages, or the last beat page fully shown when none follows

#### Scenario: Transport loss ends the round without presenting the rest
- **WHEN** a new transport generation arrives or the client detaches during playback
- **THEN** the round ends without presenting the rest

#### Scenario: The unavailable form keeps only the revision lock
- **WHEN** the completing publication carries the unavailable `combat_beats` form
- **THEN** the round is paged as its ordinary narrative response, the vitals move once
  to the committed values, and the lock is the declared-revision lock alone

#### Scenario: The presentation never touches prose, timing, or requests
- **WHEN** any part of the beat presentation runs
- **THEN** it parses no narrative prose, delays no committed value or mode, and changes
  no request
