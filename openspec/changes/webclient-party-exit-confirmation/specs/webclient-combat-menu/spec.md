# Spec Delta

## MODIFIED Requirements

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL preserve the root inventory of the client
combat-menu resolver (the root list of `web/static/webclient/js/elosern/combat_menu.js`:
Attack, Skills, Items, the client-local Bag drawer opener, Defend, Dodge, Taunt, Retreat, and the
confirmed Surrender entry) and their existing availability/order. Dodge and Taunt SHALL join Defend as actor-scoped basic actions. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop
one level, and disabled entries SHALL send no packet.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.command` with the guarded selected actor and skill payload for `basic_attack` exactly once and the draft facade saves it and resolves only a complete valid round

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the selected actor has an eligible item, Defend, Dodge or Taunt choice
- **THEN** the shared menu permits its complete selection flow and no not_implemented placeholder blocks it; disabled reasons reflect actual actor capability

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the Surrender entry but has not confirmed
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
- **THEN** the guarded combat.command envelope names the commanded actor; its skill payload is identical to the same skill, scale and target chosen without master-detail

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
- **WHEN** the player opens the Surrender entry
- **THEN** a warning panel renders with a cancel row and a confirm row, no mutation is sent, and only activating the confirm row emits one combat.exit_confirm carrying session_id, round_revision, operation and the server confirmation_token

#### Scenario: The forfeit warning states the consequence
- **WHEN** the forfeit confirmation screen renders
- **THEN** it is an explicit warning panel stating what forfeiting does

#### Scenario: Each root action keeps its dedicated route
- **WHEN** the player activates each entry of the preserved root inventory
- **THEN** Attack selects targets for innate `basic_attack`; Skills opens the committed
  skill categories as a bounded master-detail rather than one flat list; Items opens the selected actor inventory-use flow; Defend and Dodge confirm their round choice; Taunt selects one server-listed enemy; Bag inspection stays free; Retreat and Surrender open their mandatory party confirmation routes

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

## ADDED Requirements

### Requirement: Browser party exits require a safe-default party consequence dialog
Retreat and Surrender SHALL remain reachable independently of commanded member. The browser SHALL request a server session/round/operation-bound prompt, display whole-party consequences and require explicit Yes through the existing modal question card with initial No. Background commands SHALL be inert. Cancel SHALL preserve the draft and prior selection.

#### Scenario: Cancel and focus
- **WHEN** an exit dialog opens from an arbitrary member menu and the player presses No, close or Escape
- **THEN** no exit confirmation is sent, every draft entry remains and focus returns to the prior actor/menu selection

#### Scenario: Confirmed operation
- **WHEN** the player activates Yes with a valid current token
- **THEN** exactly one guarded party confirmation is sent and canonical retreat-failure, success or surrender state replaces the view

#### Scenario: Invalidation and replay
- **WHEN** session/round/epoch changes, disconnect occurs or the token becomes stale
- **THEN** pending confirmation is canceled without auto-retry and no personal flee or retired action route can mutate

