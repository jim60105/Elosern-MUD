## MODIFIED Requirements

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL present Attack, Skills, Items, Defend, and Flee in that stable order, with confirmed Forfeit under a secondary menu. Attack SHALL select targets for innate `basic_attack`; Skills SHALL open the committed skill categories as a bounded master-detail rather than one flat list; Items and Defend SHALL remain focusable but disabled with code `not_implemented`; Flee SHALL invoke the innate flee path; and Forfeit SHALL require an explicit confirmation screen. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop one level, and disabled entries SHALL send no packet.

The root SHALL render as a single row of icon-and-label tabs and SHALL declare a column count equal to its item count — including the recovery state, whose root is the confirmed Forfeit path alone — so the horizontal arrow keys traverse the tabs in their rendered order and the vertical arrow keys are a no-op on the root. The Skills tab SHALL carry a count badge equal to the flattened count of skill descriptors the committed panel actually lists.

The skill master-detail SHALL be: a category frame listing one entry per committed category group with its label and its own descriptor count; then, only when that category carries more than one sub-group, a group frame listing its sub-groups; then the skill frame listing that group's descriptors, each row carrying the skill's label and resource cost, beside the detail pane that names the focused skill, its description, its cost, its target requirement, and its server-authored reason when it is unavailable. A category carrying exactly one sub-group SHALL open the skill frame directly, so no level ever offers a single choice. Every level SHALL preserve the committed panel's order exactly and SHALL NOT reorder, filter, merge, or paginate it, and SHALL NOT render a badge or field the descriptor does not carry — in particular no out-of-combat marker, which no presenter serializes. The focused row SHALL be scrolled into view within the dock's bounded row region on every frame render and focus change. Escape SHALL pop exactly one of these levels at a time, and the subsequent scale and target steps SHALL be unchanged in behaviour and in payload.

Combat SHALL additionally present a display-only participant frame in the HUD island area, grouping the committed participants into the player's side and the opposing side in presenter order, each showing its session token, display name, current and maximum hit points as numerals, and its state with an explicit text marker for any non-active state. Each participant's portrait SHALL be resolved only by looking its server-authored `portrait_ref` up in the committed art panel's portrait catalog, with no client-constructed subject key or URL and no portrait at all for a null reference or an unavailable art panel. The frame SHALL NOT be a row container, a tab stop, or part of the dock's composite widget; target selection remains the dock's target frame.

The Forfeit confirmation SHALL render as an explicit warning panel stating what forfeiting does, with a cancel row and a confirm row; only the confirm row SHALL submit, carrying the current session identifier.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.cast` for `basic_attack` exactly once and the ordinary combat-session path resolves the result

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the player focuses Items or Defend and presses Enter
- **THEN** its `not_implemented` explanation remains readable and no `ui_action` message is emitted

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the secondary Forfeit entry but has not confirmed
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

#### Scenario: The root tab geometry matches its rendered order
- **WHEN** the player presses the horizontal arrow keys on the combat root
- **THEN** focus moves through Attack, Skills, Items, Defend, Flee, and Forfeit in their rendered order, and the vertical arrow keys move focus nowhere

#### Scenario: The participant frame renders the committed session
- **WHEN** a combat session commits participants on both teams, one of them fled or knocked out
- **THEN** the participant frame renders both sides in presenter order with each participant's token, display name, current and maximum hit points, and an explicit text marker for the non-active state, and it is not reachable by sequential keyboard navigation

#### Scenario: A participant portrait comes only from the catalog
- **WHEN** a participant carries a `portrait_ref` present in the committed portrait catalog, and another carries `null`
- **THEN** the first renders that catalog entry (including its placeholder card) and the second renders no portrait, and the browser constructs no subject key or URL

#### Scenario: The forfeit confirmation is an explicit two-step panel
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, no mutation is sent, and only activating the confirm row emits one `combat.forfeit` carrying the current session identifier
