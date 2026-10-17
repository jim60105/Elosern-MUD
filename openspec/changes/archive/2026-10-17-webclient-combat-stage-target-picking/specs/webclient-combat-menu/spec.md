## ADDED Requirements

### Requirement: Combat targets are picked on the stage figures
While the current combat frame is the target frame of an enabled SINGLE, SELF or AREA skill (the stage target step), the client SHALL let the player choose targets on the stage figures instead of in the card's rows. The frame's items, their server order, the keyboard router, the digit picks, Escape, Space and every dispatch payload SHALL stay unchanged; the client SHALL only map the arrow keys and pointer onto the frame's existing items.

#### Scenario: Each TargetSpec maps onto stage positions
- **WHEN** the target frame of an enabled skill opens for each TargetSpec
- **THEN** SINGLE has one position per server candidate (its `target-<id>` item); SELF has one position, its `self-confirm` item, on the controlled figure; AREA has one position per candidate (its `area-<id>` item), then one group position per approved shorthand the skill carries (its `shorthand-<key>` item), then the `area-confirm` position; NONE and a disabled skill's frame start no stage target step and render their rows in the card as before

#### Scenario: Positions follow stage order
- **WHEN** the stage target step builds its positions with a four-figure party and nine standing foes in two ranks, all of them candidates, and a fled participant the server still lists
- **THEN** the member positions run in the formation's stage order — every drawn figure by the horizontal centre of its formation box, from left to right (the front rank first on a tie), so the party comes before the foes — followed by candidates no stage figure draws (only a fled participant can be one) in the server's order, then (AREA) the group positions in the server's shorthand order, then the confirm position; the order is the formation engine's stage order, never measured from the DOM

#### Scenario: Arrow keys move along the stage
- **WHEN** the player presses ArrowRight, ArrowDown, ArrowLeft and ArrowUp in a stage target step with four positions
- **THEN** ArrowRight and ArrowDown move the frame's focus to the next position in stage order and ArrowLeft and ArrowUp to the previous one, each wrapping at the ends, through the router's existing focus-by-key operation; in a SELF step every arrow keeps the focus where it is; when the frame's focus is on an item that is no position (such as a back row), ArrowRight and ArrowDown move to the first position and ArrowLeft and ArrowUp to the last; outside the stage target step the arrow keys reach the router unchanged

#### Scenario: Enter, Space, digits and Escape keep their meaning
- **WHEN** the player presses Enter on a SINGLE position, Space and then Enter on an AREA member, Enter on an AREA group position, Enter on the AREA confirm position, a digit, and Escape
- **THEN** Enter on the SINGLE position submits one `combat.cast` whose `target_ids` is that candidate; Space and Enter on the AREA member each toggle its selection; Enter on a group position chooses that shorthand; Enter on the confirm position submits the AREA payload; a digit N focuses and activates the frame's N-th item in the server's order; Escape pops exactly one frame and the stage leaves the step in that frame; every payload is byte-identical to the one the same choice produced from the card's rows

#### Scenario: The opening focus is unchanged
- **WHEN** the player opens Attack, and separately a skill whose first server candidate is an ally
- **THEN** Attack opens focused on the first enabled foe the server listed and the other skill on the frame's first item, exactly as the card's rows did; nothing is selected or sent

#### Scenario: Pointer picks a figure
- **WHEN** the player moves the pointer over a selectable foe's figure, then clicks it, and in an AREA step clicks a group chip and the confirm chip in the target prompt
- **THEN** hovering focuses that foe's position, the click focuses it and activates it through the router's confirm with a pointer source, sending exactly one `combat.cast` for a SINGLE step and toggling the member for an AREA step, and the chips choose their shorthand and submit the AREA payload; after a chip click DOM focus is back on `#action-dock`, so a following Enter activates the focused position rather than the chip; a figure that is not a candidate takes no pointer

#### Scenario: Whole-group positions light the group
- **WHEN** an AREA skill carries the shorthands `all-enemies` and `all-allies` and the player moves onto the `all-enemies` position, then to `all-allies`, then presses Enter and moves to the confirm position
- **THEN** each group is one position whose lit set is every candidate of that side, the focus moves between the groups and never between their members, Enter chooses `all-allies` and clears any explicit selection, and the confirm position's lit set is the chosen group; confirming sends one request carrying `target_shorthand: "all-allies"` and no target-ID field

#### Scenario: AREA explicit selection stays visible
- **WHEN** the player toggles two foes with Space and moves the focus to the confirm position
- **THEN** both foes carry the selected mark while the focus is elsewhere, the confirm position's lit set is exactly those two foes, and confirming sends their identities in presenter order

#### Scenario: A SELF skill lights the controlled figure
- **WHEN** the target frame of an enabled SELF skill opens
- **THEN** the only position is on the controlled figure, which is lit with the arrow marker, Enter submits the payload without any target field, and the arrow keys keep the focus

#### Scenario: Knocked-out and unlisted participants
- **WHEN** a revive-style SINGLE skill lists a knocked-out companion and a knocked-out foe as candidates while a defeated foe is not listed
- **THEN** the knocked-out companion and the knocked-out foe are positions on their stage figures, which keep their fallen treatment and carry the arrow marker, and the unlisted defeated foe is no position and carries no marker

#### Scenario: A changing target set follows the panel
- **WHEN** a committed panel replacement removes the focused candidate while the stage target step is open, and later a replacement adds a candidate
- **THEN** the existing repair moves the focus to the nearest surviving item, the lit set and the markers follow in the same frame so no vanished figure stays lit, and the added candidate gains its position in stage order

#### Scenario: Playback suspends the step
- **WHEN** a combat round starts playing while the stage target step is open
- **THEN** the arrow keys are not claimed, no position is lit or marked, and no figure carries the step's dim while the round plays; if the frame is still current when the round ends, the step resumes with its focus

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
- **THEN** the frame's items stay in the server's order, the card collapses to the target prompt, each candidate is a position on its stage figure, ArrowRight and ArrowDown move to the next position in stage order, ArrowLeft and ArrowUp to the previous one, each wrapping, and the digits 1–3 pick the candidates in the server's order

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
- **THEN** the no-target frame renders as the same single-column list; the single-target,
  self, and AREA frames keep their items in the server's candidate order, are chosen on the
  stage figures, and the target prompt and the live announcement name each focused
  target's side as well as its name

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
  targets are chosen in the stage target step

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
