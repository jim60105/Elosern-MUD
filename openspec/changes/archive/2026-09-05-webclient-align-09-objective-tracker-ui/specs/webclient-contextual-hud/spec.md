# Delta spec: webclient-contextual-hud (webclient-align-09-objective-tracker-ui)

## ADDED Requirements

### Requirement: The objective tracker island presents the committed objectives only
The HUD SHALL carry a bottom-right objective tracker island while the committed `objectives`
panel is available with a non-empty `rows` list in exploration or combat mode, and SHALL render no
tracker island when `rows` is empty, when the panel is unavailable, or in creation mode. The
island's header SHALL read `目標` with the mono-gold count `N 追蹤`, where `N` equals the
committed row count. Each row of `objectives.rows` SHALL render, in payload order: a stage box
showing a completion check when `stage_progress >= objective_quantity` and an empty box
otherwise; the row's `objective_line`; a right-aligned mono-gold slot carrying
`stage_progress / objective_quantity` when `objective_quantity` is greater than one and the
row's `+reward_copper` when `objective_quantity` is one and `reward_copper` is non-null, and
carrying nothing otherwise; and, when `deadline_line` is non-null, a trailing muted line with
that text. The tracker is display-only: it SHALL render no accept, abandon, turn-in, or tracking
control and SHALL dispatch no action. It SHALL present no objective prose the panel does not
carry and no invented optional or previous-stage rows.

#### Scenario: Active objectives list in payload order
- **WHEN** a snapshot commits two objective rows, the first with progress 2 of quantity 5 and the
  second a single-count quest with an 80-copper reward
- **THEN** the island reads `目標 2 追蹤` and renders the first row's `2/5` progress tag and the
  second row's `+80` tag with their describe-seam objective lines, and no control is present

#### Scenario: A satisfied objective shows the done box
- **WHEN** a committed row carries `stage_progress` equal to `objective_quantity`
- **THEN** that row's stage box renders the completion check

#### Scenario: An empty or unavailable objective list hides the island
- **WHEN** the committed `objectives.rows` becomes `[]` or the panel becomes unavailable
- **THEN** no tracker island is rendered anywhere in the HUD

#### Scenario: The tracker dispatches nothing
- **WHEN** the player interacts with the tracker island
- **THEN** no `ui_action` or text command is sent and no mutation control is present
