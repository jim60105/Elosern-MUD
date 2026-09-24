## MODIFIED Requirements

### Requirement: The exploration dock renders the suggestions section from the validated v5 panel

In exploration mode the action-dock surface SHALL render the `suggestions` content derived from the
`context_actions` panel the store already validated (mirror-accepted at commit time) as its own dock
pane, reached from the scene overview's footer chip, labelled `建議 (N)` with N the number of cards the
pane will list when N is positive and `建議` otherwise. The pane SHALL be a menu frame of the keyboard router like every other dock
frame, so its cards are focusable rows reachable by arrow keys and by pointer through the identical
gate, and Escape or the breadcrumb's back control returns to the overview with the 建議 chip focused. The four renders are exactly:

- `status = "generating"`: the footer chip is present labelled `建議` with no count, and its pane holds one
  muted, focusable, non-submitting row reading "AI 正在構思建議…", no cards, no dismiss control.
- `status = "ready"`: the pane SHALL show between 3 and 5 clickable suggestion cards (the
  bound the server validator enforces for ready sets), each with its label and optional hint, and
  a "✕ 清除建議" dismiss row.
- `status = "degraded"`: the pane SHALL show rule cards (0–5; the v1 exploration derivation
  always yields ≥ 1) plus one muted "AI 建議目前不可用" note and the same dismiss row.
- `status = "unavailable"`: no 建議 footer chip SHALL be presented and no pane SHALL exist, so the
  surface renders nothing at all for suggestions.

The dismiss control SHALL dispatch the same envelope it dispatches today and SHALL be rendered as a
row of the pane rather than a corner control, so it is not a second tab stop inside the dock's
composite widget. The pane SHALL appear only while the exploration dock owns the surface (never in
combat or creation mode, and never while a re-homed services/character sub-dock is active), SHALL be
torn down with the dock on mode exit, and SHALL derive its status, card list, and visibility through a
DOM-independent view function so every status is testable without a browser. A panel update that
changes only the suggestions content SHALL replace the pane's rows in place without rebuilding the
dock, without popping the frame, and without resetting the keyboard router to another frame; when the
pane is the current frame, focus SHALL be preserved on a card whose action code and parameters survive
the update and SHALL otherwise land deterministically on the nearest surviving row. Repeated
`generating` statuses are never separately published by the trigger service; any dock rebuild that
does occur SHALL render an equivalent generating row (no DOM-identity promise across rebuilds). All
text SHALL be rendered as literal text nodes — never through an HTML/markup pipeline.

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
