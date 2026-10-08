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

In exploration mode the action-dock surface SHALL render the `suggestions` content derived from the
`context_actions` panel the store already validated (mirror-accepted at commit time) as its own dock
pane, reached from the scene overview's footer chip, labelled `建議 (N)` with N the number of cards the
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

### Requirement: One shared card component renders every suggestion card

A single card component SHALL build every suggestion card as a native `<button>` element from the
validated card fields (`kind`, `action_code`, `label`, `params`, optional `hint`) — the same
component the dock embeds and the later narrative choice-point slice reuses, so both surfaces
cannot diverge. Both forms SHALL come from that one component, never from a second card renderer.

#### Scenario: The dock and the choice-point surface share one builder
- **WHEN** a `known_action` card and a `freeform` card with hint are rendered by the component
- **THEN** each produces a button with the exact label text, the hint rendered as a plain text
  line where present, and the dismiss control is separate from both

#### Scenario: One component renders both the dock row and the choice-point button
- **WHEN** the same card is rendered into the dock's suggestions pane and into the narrative
  choice-point
- **THEN** the dock instance is a row of the dock's active row container with the option role and a
  row identity attribute while the choice-point instance stays a natively tab-focusable button, and
  both are produced by the one shared component with identical label, hint and click contract

#### Scenario: The dock row form keeps one composite widget
- **WHEN** the dock embeds the component
- **THEN** the card additionally carries its selected state attribute, so the dock keeps exactly one
  composite widget and one tab stop; where the narrative choice-point embeds it, the card stays a
  natively tab-focusable button

#### Scenario: Each card kind carries its defined text
- **WHEN** a card is rendered by the component
- **THEN** the `known_action` card carries its label and optional hint, and the `freeform` card
  carries its label (the phrase the player speaks, by contract)

#### Scenario: The dismiss control renders once per surface
- **WHEN** a suggestions surface renders its dismiss control
- **THEN** it is rendered once per suggestions surface, not per card, appears for both `ready` and
  `degraded` states, and appears as a row of the pane where the dock hosts it and as a separate
  small button where another surface hosts it

#### Scenario: Card text never enters a markup pipeline
- **WHEN** any card text renders
- **THEN** it is rendered as a literal text node, and no content from a card may ever enter a markup
  allowlist pipeline

### Requirement: Suggestion cards execute exact envelopes through the action client

Activating a suggestion card or its dismiss control SHALL dispatch through the existing action
client (`window.Elosern.actions.submit`) — no new OOB message type, no envelope change. In both
hosting forms the dispatched envelopes are exactly:

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
- **WHEN** the player activates "✕ 清除建議" while the pane shows `ready` or `degraded` cards
- **THEN** the client submits `options.dismiss` with an empty payload, and once the published
  `unavailable` state arrives, the 建議 root entry and its pane disappear from the dock (the
  narrative-stream choice-point removal is specified and tested by the later choice-point slice)

#### Scenario: A dock-hosted card submits exactly what its keyboard confirmation submits
- **WHEN** the player activates a card in the dock's suggestions pane with the pointer, and then
  confirms the same card with Enter
- **THEN** each deliberate activation emits exactly one `ui_action` with the identical action code
  and payload, and an activation while the action client is locked emits nothing

#### Scenario: The freeform speech is always the label
- **WHEN** a `freeform` card is activated on any surface
- **THEN** the submitted `speech` is always the label text

#### Scenario: A dock-hosted activation traverses the router path
- **WHEN** the dock hosts the card as a row of its suggestions frame and the card is activated
- **THEN** activation traverses the ordinary router path every other dock row traverses — the
  delegated pointer bridge's `[data-item-key]` row handling, the shared focus, disabled-explanation
  and submission gates, and the identical keyboard confirmation — and still ignores
  keyboard-synthesized clicks

#### Scenario: A non-dock activation bypasses the router
- **WHEN** another surface hosts the card and it is activated
- **THEN** activation uses the direct click handler on the native button and does not involve the
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
- **WHEN** a card is hosted outside the dock, and separately as a dock row
- **THEN** the outside card remains natively tab-focusable and pointer-activatable, while the dock
  row is reachable by the dock's arrow-key navigation and by pointer but NOT individually reachable
  by sequential keyboard navigation, because the dock is one composite widget with a single tab stop

### Requirement: A degraded payload with zero cards renders the defined empty-state

A `degraded` payload carrying an empty card list SHALL render the muted line
"現在沒有什麼值得做的動作" as the suggestions pane's body (never an empty container and never a
failure), alongside the muted unavailability note and the dismiss row.

#### Scenario: Zero-card degraded renders the empty-state line
- **WHEN** the store presents a `degraded` suggestions payload with an empty `cards` array
- **THEN** the pane body shows "現在沒有什麼值得做的動作" together with the "AI 建議目前
  不可用" note and the dismiss row, the 建議 root entry carries no badge, and no crash or empty box
  is rendered

#### Scenario: A missing suggestions field degrades silently as a compatibility guard
- **WHEN** a pre-v5 `context_actions` panel (no `suggestions` field) reaches the dock through the
  store
- **THEN** no 建議 root entry is presented, the dock's other content is unaffected, and the
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
