## MODIFIED Requirements

### Requirement: The objective tracker island presents the committed objectives only
The HUD SHALL carry the objective tracker as an instrument panel in the stage's `map` anchor, directly beneath the minimap, while the committed mode is exploration and the committed `objectives` panel is available with non-empty `rows`; it SHALL be `display:none` in combat and dialogue and SHALL render nothing when `rows` is empty, the panel is unavailable, or in creation. Its objective line SHALL stay one text row.

#### Scenario: The line's contents follow one fixed order
- **WHEN** the tracker line renders
- **THEN** the region's accessible name is 目標 and no visible 目標 label renders; the line carries, in order: a completion marker for the first row of `objectives.rows` whose shape is open while that row's `stage_progress < objective_quantity` and filled with a check once `stage_progress >= objective_quantity`, with an accessible name stating which (進行中 or 已達成); that first row's `objective_line`, truncated on one line with an overflow indicator while its full text stays the line's accessible text and tooltip; a tabular readout of `stage_progress` then `/ objective_quantity` when the first row's `objective_quantity` is greater than one, its `+reward_copper` in the gold mono face when `objective_quantity` is one and `reward_copper` is non-null, and nothing otherwise; and, when more than one row is committed, a further-rows count showing `N` (the number of further rows) beside a stacked-lines glyph, with no plus sign, whose accessible name states that `N` further tracked objectives exist (另有 N 項追蹤目標)

#### Scenario: Later rows and deadlines belong to the quest drawer
- **WHEN** rows after the first, or any row's `deadline_line`, exist
- **THEN** they are not rendered on the stage; the quest drawer presents them

#### Scenario: The tracker is display-only and never invents
- **WHEN** the tracker renders
- **THEN** it renders no accept, abandon, turn-in, or tracking control and dispatches no action, and presents no objective prose the panel does not carry and no invented optional or previous-stage rows

#### Scenario: Active objectives list in payload order
- **WHEN** a snapshot commits two objective rows in exploration mode, the first with progress 2 of quantity 5 and the
  second a single-count quest with an 80-copper reward
- **THEN** the region is named 目標, the line renders the first row's describe-seam objective line with
  its readout of 2 then `/ 5` and a further-rows count of 1, the second row's objective line and `+80`
  tag are not rendered on the stage, the objective line keeps one text row, and no control is present

#### Scenario: A satisfied objective shows the done box
- **WHEN** the first committed row carries `stage_progress` equal to `objective_quantity`
- **THEN** the completion marker is drawn filled with a check and its accessible name states that the objective is reached, so the state never depends on colour alone

#### Scenario: An empty or unavailable objective list hides the island
- **WHEN** the committed `objectives.rows` becomes `[]` or the panel becomes unavailable
- **THEN** no objective line is rendered anywhere in the HUD

#### Scenario: The tracker dispatches nothing
- **WHEN** the player interacts with the objective line
- **THEN** no `ui_action` or text command is sent and no mutation control is present

#### Scenario: A long objective line truncates in place
- **WHEN** the first row's `objective_line` is longer than the line's width
- **THEN** the text is truncated with an overflow indicator, the line keeps one text row, and the full `objective_line` is the line's accessible text

#### Scenario: The tracker is an instrument panel
- **WHEN** the tracker renders in the live client
- **THEN** it is an instrument panel as "An instrument panel wears a feathered ground and one brass fitting instead of a box" defines, and its left and right edges coincide with the place card's (±1px)

#### Scenario: A counted objective shows one tick per unit
- **WHEN** the first row's `objective_quantity` is greater than one and at most 12
- **THEN** one tick per unit renders under the line, hidden from assistive technology; the first `stage_progress` ticks (clamped to between 0 and `objective_quantity`) are marked reached and the rest are empty

#### Scenario: A large count shows one tapering stroke
- **WHEN** the first row's `objective_quantity` is greater than 12
- **THEN** no ticks render; one continuous stroke renders under the line, hidden from assistive technology, whose filled part is `stage_progress / objective_quantity` of its length (±1px, with the progress clamped as for ticks)

#### Scenario: A single-count objective shows no quantity marks
- **WHEN** the first row's `objective_quantity` is one, absent, or not a number
- **THEN** neither ticks nor a stroke render
