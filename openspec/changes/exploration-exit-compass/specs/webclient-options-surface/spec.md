## MODIFIED Requirements

### Requirement: The exploration dock renders the suggestions section from the validated v5 panel

In exploration mode the action-dock surface SHALL render the `suggestions` content derived from the
`context_actions` panel the store already validated (mirror-accepted at commit time) as its own dock
pane, reached from the scene overview's footer chip in the right column beside the exit compass, labelled `建議 (N)` with N the number of cards the
pane will list when N is positive and `建議` otherwise. The pane SHALL be a menu frame of the keyboard
router like every other dock frame, with its four status renders defined by the scenarios below.

#### Scenario: The pane follows the four statuses
- **WHEN** a puppeted WebClient in exploration mode presents `suggestions` with status
  `generating`, then `ready` (3–5 cards), then `degraded` (rule cards), then `unavailable`
- **THEN** the 建議 pane first shows the muted generating row, then the ready card set with the
  dismiss row and the footer chip labelled `建議 (N)` with N the card count, then the degraded rule
  cards with the muted note and dismiss row, and finally the 建議 footer chip is absent altogether

#### Scenario: A suggestions-only update re-renders without a dock rebuild
- **WHEN** the exploration panel is unchanged but `suggestions.status` flips `generating` →
  `ready` in a `ui_update`
- **THEN** the pane's rows are replaced in place with the ready cards while the exploration menu
  frames are untouched, the router stays on whichever frame it was on, and no frame is popped

#### Scenario: Focus survives a suggestions-only update deterministically
- **WHEN** the 建議 pane is the current frame with a card focused and a `ui_update` replaces the card
  set
- **THEN** focus stays on that card when its action code and parameters survive the update, and
  otherwise lands deterministically on the nearest surviving row rather than resetting the router to
  another frame

#### Scenario: Cards are reachable by keyboard
- **WHEN** the player activates the 建議 footer chip with the keyboard and arrows through the pane
- **THEN** each card is a focusable row of the dock's active row container, activating one emits its
  exact envelope, and activating the dismiss row emits the dismiss envelope

#### Scenario: The pane never appears in combat or creation mode
- **WHEN** the active mode is combat or character creation while the same `context_actions`
  panel streams `suggestions`
- **THEN** the dock surface presents no 建議 chip and no suggestions pane, and returning to
  exploration mode without an available panel also presents none

#### Scenario: The pane yields to a re-homed sub-dock
- **WHEN** a re-homed services/character sub-dock is active while the exploration dock owns the surface
- **THEN** the 建議 pane does not appear until the sub-dock is closed

#### Scenario: The pane's cards are reachable rows and back returns to the chip
- **WHEN** the player navigates the 建議 pane with arrow keys or pointer, then presses Escape or the
  breadcrumb's back control
- **THEN** every card is a focusable row reached through the identical gate, and the view returns to
  the overview with the 建議 chip focused

#### Scenario: Generating renders exactly the muted row
- **WHEN** the status is `generating`
- **THEN** the footer chip is present labelled `建議` with no count, and the pane holds one muted,
  focusable, non-submitting row reading "AI 正在構思建議…", no cards, no dismiss control

#### Scenario: Ready renders three to five cards and the dismiss row
- **WHEN** the status is `ready`
- **THEN** the pane shows between 3 and 5 clickable suggestion cards (the bound the server validator
  enforces for ready sets), each with its label and optional hint, and a "✕ 清除建議" dismiss row

#### Scenario: Degraded renders rule cards with the muted note
- **WHEN** the status is `degraded`
- **THEN** the pane shows rule cards (0–5; the v1 exploration derivation always yields ≥ 1) plus one
  muted "AI 建議目前不可用" note and the same dismiss row

#### Scenario: Unavailable renders nothing
- **WHEN** the status is `unavailable`
- **THEN** no 建議 footer chip is presented and no pane exists, so the surface renders nothing at all
  for suggestions

#### Scenario: The dismiss control is a pane row with today's envelope
- **WHEN** the dismiss control is rendered
- **THEN** it dispatches the same envelope it dispatches today and appears as a row of the pane
  rather than a corner control, so it is not a second tab stop inside the dock's composite widget

#### Scenario: Mode exit tears the pane down
- **WHEN** the player leaves exploration mode
- **THEN** the 建議 pane is torn down with the dock, and the surface is owned only while the
  exploration dock owns it

#### Scenario: Status derivation is DOM-independent
- **WHEN** a test exercises every suggestions status
- **THEN** the pane's status, card list, and visibility come from a DOM-independent view function, so
  every status is testable without a browser

#### Scenario: Suggestions text is never markup
- **WHEN** any suggestions text renders
- **THEN** it is rendered as a literal text node, never through an HTML/markup pipeline

#### Scenario: A suggestions-only update replaces rows in place
- **WHEN** a panel update changes only the suggestions content
- **THEN** the pane's rows are replaced in place without rebuilding the dock, without popping the
  frame, and without resetting the keyboard router to another frame

#### Scenario: Surviving focus is preserved across a suggestions-only update
- **WHEN** the pane is the current frame during a suggestions-only update
- **THEN** focus is preserved on a card whose action code and parameters survive the update and
  otherwise lands deterministically on the nearest surviving row

#### Scenario: A rebuilt dock renders an equivalent generating row
- **WHEN** a dock rebuild occurs while the status is `generating`
- **THEN** the rebuilt pane renders an equivalent generating row, with no DOM-identity promise across
  rebuilds, because repeated `generating` statuses are never separately published by the trigger
  service

