## Purpose

The exploration dock's suggestions section surface: the four-status render contract (generating
muted line, ready card set, degraded rule cards, and no section when unavailable), the single
shared card component every suggestion card is built from, the exact envelopes cards and the
dismiss control dispatch through the action client, and the defined empty-state fallback for a
zero-card degraded payload. The server-side trigger that produces `suggestions` content is
specified by the context-actions-suggestions and action-options-trigger-* capabilities; this
capability pins the dock's read-side render contract.

## Requirements

### Requirement: The exploration dock renders the suggestions section from the validated v5 panel

In exploration mode the client SHALL render the `suggestions` content derived from the validated
`context_actions` panel on the centred suggestions card, opened by the 建議 pill at the top right of the
command panel beside the exit compass, labelled `建議 N` with N the card count when N is positive and `建議`
otherwise (`webclient-room-actions`). The card SHALL be client-local, never a router frame, with its four
status renders defined by the scenarios below.

#### Scenario: The pane follows the four statuses
- **WHEN** a puppeted WebClient in exploration mode presents `suggestions` with status
  `generating`, then `ready` (3–5 cards), then `degraded` (rule cards), then `unavailable`
- **THEN** the suggestions card first shows the muted generating note, then the ready card set with
  the dismiss row and the pill labelled `建議 N` with N the card count, then the degraded rule cards
  with the muted note and dismiss row, and finally the 建議 pill and the card are absent altogether

#### Scenario: A suggestions-only update re-renders without a dock rebuild
- **WHEN** the exploration panel is unchanged but `suggestions.status` flips `generating` →
  `ready` in a `ui_update`
- **THEN** the open card's rows are replaced in place with the ready cards on the same card element,
  the router stays on whichever frame it was on, and no frame is popped

#### Scenario: Focus survives a suggestions-only update deterministically
- **WHEN** the suggestions card is open with a card row active and a `ui_update` replaces the card
  set
- **THEN** the active row stays on that card when its action code and parameters survive the update,
  and otherwise stays deterministically at its position in range, never closing the card

#### Scenario: Cards are reachable by keyboard
- **WHEN** the player activates the 建議 pill with the keyboard and arrows through the card
- **THEN** each card is a row of the card's one keyboard composite, activating one emits its exact
  envelope, and activating the dismiss row emits the dismiss envelope

#### Scenario: The pane never appears in combat or creation mode
- **WHEN** the active mode is combat or character creation while the same `context_actions`
  panel streams `suggestions`
- **THEN** the client presents no 建議 pill and no suggestions card (an open card closes in the
  commit that leaves exploration), and returning to exploration mode without an available panel also
  presents none

#### Scenario: The pane yields to a re-homed sub-dock
- **WHEN** a re-homed services/character sub-dock is active while the exploration dock owns the surface
- **THEN** the 建議 pill and the suggestions card do not appear (an open card closes) until the
  sub-dock is closed

#### Scenario: The pane's cards are reachable rows and back returns to the chip
- **WHEN** the player navigates the suggestions card with arrow keys or pointer, then presses Escape
  or its `✕ 返回` row
- **THEN** every card row is activated through the identical gate, and the card closes with focus
  returned to the 建議 pill

#### Scenario: Generating renders exactly the muted row
- **WHEN** the status is `generating`
- **THEN** the pill is present labelled `建議` with no count, and the card holds one muted,
  non-selectable note reading "AI 正在構思建議…", no cards, no dismiss row

#### Scenario: Ready renders three to five cards and the dismiss row
- **WHEN** the status is `ready`
- **THEN** the card shows between 3 and 5 activatable suggestion rows (the bound the server validator
  enforces for ready sets), each with its label and optional hint, and a "清除建議" dismiss row marked
  with a trash-can icon above the trailing `✕ 返回`

#### Scenario: Degraded renders rule cards with the muted note
- **WHEN** the status is `degraded`
- **THEN** the card shows rule cards (0–5; the v1 exploration derivation always yields ≥ 1) plus one
  muted "AI 建議目前不可用" note and the same dismiss row

#### Scenario: Unavailable renders nothing
- **WHEN** the status is `unavailable`
- **THEN** no 建議 pill is presented and no card exists (an open card closes in that commit), so the
  surface renders nothing at all for suggestions

#### Scenario: The dismiss control is a pane row with today's envelope
- **WHEN** the dismiss control is rendered
- **THEN** it dispatches the same envelope it dispatches today and appears as a row of the card
  rather than a corner control, so it is not a second tab stop inside the card's composite

#### Scenario: Mode exit tears the pane down
- **WHEN** the player leaves exploration mode
- **THEN** the suggestions card closes and the 建議 pill leaves with the exploration root, and the
  surface exists only while the exploration screen does

#### Scenario: Status derivation is DOM-independent
- **WHEN** a test exercises every suggestions status
- **THEN** the card's status, rows, and notes and the pill's visibility come from DOM-independent
  builders, so every status is testable without a browser

#### Scenario: Suggestions text is never markup
- **WHEN** any suggestions text renders
- **THEN** it is rendered as a literal text node, never through an HTML/markup pipeline

#### Scenario: A suggestions-only update replaces rows in place
- **WHEN** a panel update changes only the suggestions content
- **THEN** the open card's rows are replaced in place without rebuilding the card, without pushing
  or popping a frame, and without resetting the keyboard router

#### Scenario: Surviving focus is preserved across a suggestions-only update
- **WHEN** the suggestions card is open during a suggestions-only update
- **THEN** the active row is preserved on a card whose action code and parameters survive the update
  and otherwise stays deterministically at its position in range

#### Scenario: A rebuilt dock renders an equivalent generating row
- **WHEN** the card is re-opened while the status is `generating`
- **THEN** the re-opened card renders an equivalent generating note, with no DOM-identity promise across
  rebuilds, because repeated `generating` statuses are never separately published by the trigger
  service

### Requirement: One shared card component renders every suggestion card

The one centred card shell, `ChoiceCard`, SHALL render every suggestion card as a row built from the
validated card fields (`kind`, `action_code`, `label`, `params`, optional `hint`), through the one
suggestions-row builder the store and the card share, so no second card renderer exists (the retired
`OptionCard` and `ChoiceCardRow` are gone).

#### Scenario: The dock and the choice-point surface share one builder
- **WHEN** a `known_action` card and a `freeform` card with hint are rendered by the card
- **THEN** each produces a row with the exact label text, the hint rendered as a plain text second
  line where present, and the dismiss row is separate from both

#### Scenario: One component renders both the dock row and the choice-point button
- **WHEN** a card is rendered on the suggestions card
- **THEN** it is a menu item of the card's one keyboard composite with a row identity attribute,
  produced by the one shared component with one label, hint, and activation contract

#### Scenario: The dock row form keeps one composite widget
- **WHEN** the suggestions card renders its rows
- **THEN** the card is exactly one composite widget and one tab stop that names its active row
  through an active-descendant reference

#### Scenario: Each card kind carries its defined text
- **WHEN** a card is rendered by the component
- **THEN** the `known_action` card carries its label and optional hint, and the `freeform` card
  carries its label (the phrase the player speaks, by contract)

#### Scenario: The dismiss control renders once per surface
- **WHEN** a suggestions surface renders its dismiss control
- **THEN** it is rendered once per suggestions surface, not per card, appears for both `ready` and
  `degraded` states, and appears as the card's 清除建議 row

#### Scenario: Card text never enters a markup pipeline
- **WHEN** any card text renders
- **THEN** it is rendered as a literal text node, and no content from a card may ever enter a markup
  allowlist pipeline

### Requirement: Suggestion cards execute exact envelopes through the action client

Activating a suggestion card or its dismiss control SHALL dispatch through the existing action
client (`window.Elosern.actions.submit`) — no new OOB message type, no envelope change. The
dispatched envelopes are exactly:

- `known_action` card → `submit(action_code, params)` with the card's validator-normalized payload as-is.
- `freeform` card → `submit("explore.talk_freeform", {"npc_id": params.npc_id, "speech": label})`.
- Dismiss control → `submit("options.dismiss", {})`.

#### Scenario: Clicking a ready card dispatches its exact envelope
- **WHEN** the player clicks a `known_action` card (`"explore.move"` with
  `{exit_ref, current_node}`) and then clicks a `freeform` card for NPC 7 labeled
  "我們聊聊好嗎？"
- **THEN** the client submits `ui_action` envelopes for `explore.move` with the card's payload
  unchanged and for `explore.talk_freeform` with `{npc_id: 7, speech: "我們聊聊好嗎？"}`, and
  neither dispatch echoes a command line

#### Scenario: The dismiss control hides the suggestions surface
- **WHEN** the player activates "清除建議" while the card shows `ready` or `degraded` cards
- **THEN** the client submits `options.dismiss` with an empty payload, and once the published
  `unavailable` state arrives the card and the 建議 pill leave together — the committed envelope,
  never the local dispatch, decides the removal (the preserved dismiss invariant
  `webclient-context-actions-suggestions` restates)

#### Scenario: A dock-hosted card submits exactly what its keyboard confirmation submits
- **WHEN** the player activates a card on the suggestions card with the pointer, and then confirms
  the same card with Enter
- **THEN** each deliberate activation emits exactly one `ui_action` with the identical action code
  and payload, and an activation while the action client is locked emits nothing

#### Scenario: The freeform speech is always the label
- **WHEN** a `freeform` card is activated on any surface
- **THEN** the submitted `speech` is always the label text

#### Scenario: A dock-hosted activation traverses the router path
- **WHEN** a card row on the suggestions card is activated
- **THEN** the row is re-resolved from the committed envelope and traverses the one gated
  exploration activation every exploration row outside the router shares — the in-flight and
  awaiting-revision lock and the single dispatch entry — identically for pointer and keyboard

#### Scenario: A non-dock activation bypasses the router
- **WHEN** a suggestion card is activated
- **THEN** activation uses the card's own click and keydown handlers and does not involve the
  KeyboardRouter

#### Scenario: Card activations are never echoed
- **WHEN** a suggestion card is activated
- **THEN** it is not echoed as a command line, because no display descriptor exists for suggestion
  cards and the existing echo bridge stays silent

#### Scenario: A locked client rejects the submit cleanly
- **WHEN** the action client is locked (offline, synchronizing, or another mutation in flight) and a
  card or dismiss control is activated
- **THEN** the submit is rejected without side effects, exactly as for every other action

#### Scenario: Tab reachability differs by host
- **WHEN** the suggestions card is open
- **THEN** its rows are reachable by the card's arrow-key navigation, its digits, and the pointer but
  NOT individually by sequential keyboard navigation, because the card is one composite widget with a
  single tab stop that traps focus until it closes

### Requirement: A degraded payload with zero cards renders the defined empty-state

A `degraded` payload carrying an empty card list SHALL render the muted line
"現在沒有什麼值得做的動作" as the suggestions card's body (never an empty container and never a
failure), alongside the muted unavailability note and the dismiss row.

#### Scenario: Zero-card degraded renders the empty-state line
- **WHEN** the store presents a `degraded` suggestions payload with an empty `cards` array
- **THEN** the card body shows "現在沒有什麼值得做的動作" together with the "AI 建議目前
  不可用" note and the dismiss row, the 建議 pill carries no count, and no crash or empty box
  is rendered

#### Scenario: A missing suggestions field degrades silently as a compatibility guard
- **WHEN** a pre-v5 `context_actions` panel (no `suggestions` field) reaches the exploration screen
  through the store
- **THEN** no 建議 pill is presented, the screen's other content is unaffected, and the
  guard's presence is documented as compatibility-only rather than a normal v5 case

#### Scenario: The empty-state is unreachable in v1 by construction
- **WHEN** the v1 exploration derivation produces rule cards
- **THEN** it always yields at least one rule card, so the zero-card degraded state is unreachable
  in v1 and exists purely as a safe fallback for future kinds without an idle baseline

#### Scenario: A missing suggestions field is never a valid v5 case
- **WHEN** a `v5` payload arrives with a **missing** `suggestions` field
- **THEN** it is never a valid case (the v5 contract requires the field in every payload), and the
  view treating it as `unavailable` is only a defensive compatibility guard for pre-v5 panels or a
  not-yet-landed mirror, never a normal render path
