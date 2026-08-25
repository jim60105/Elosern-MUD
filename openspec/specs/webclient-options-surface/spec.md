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
pane, reached from a root entry labelled 建議 that carries a count badge equal to the number of cards
the pane will list. The pane SHALL be a menu frame of the keyboard router like every other dock
frame, so its cards are focusable rows reachable by arrow keys and by pointer through the identical
gate, and Escape or the breadcrumb's back control returns to the root. The four renders are exactly:

- `status = "generating"`: the 建議 root entry is present with no badge, and its pane holds one
  muted, focusable, non-submitting row reading "AI 正在構思建議…", no cards, no dismiss control.
- `status = "ready"`: the pane SHALL show between 3 and 5 clickable suggestion cards (the
  bound the server validator enforces for ready sets), each with its label and optional hint, and
  a "✕ 清除建議" dismiss row.
- `status = "degraded"`: the pane SHALL show rule cards (0–5; the v1 exploration derivation
  always yields ≥ 1) plus one muted "AI 建議目前不可用" note and the same dismiss row.
- `status = "unavailable"`: no 建議 root entry SHALL be presented and no pane SHALL exist, so the
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
  dismiss row and a badge equal to the card count, then the degraded rule cards with the muted note
  and dismiss row, and finally the 建議 root entry is absent altogether

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
- **WHEN** the player opens the 建議 root entry with the keyboard and arrows through the pane
- **THEN** each card is a focusable row of the dock's active row container, activating one emits its
  exact envelope, and activating the dismiss row emits the dismiss envelope

#### Scenario: The pane never appears in combat or creation mode
- **WHEN** the active mode is combat or character creation while the same `context_actions`
  panel streams `suggestions`
- **THEN** the dock surface presents no 建議 root entry and no suggestions pane, and returning to
  exploration mode without an available panel also presents none

### Requirement: One shared card component renders every suggestion card

A single card component SHALL build every suggestion card as native `<button>` elements from the
validated card fields (`kind`, `action_code`, `label`, `params`, optional `hint`) — the same
component the dock embeds and the later narrative choice-point slice reuses, so both surfaces
cannot diverge. Where the dock embeds it, the component SHALL additionally render the card as a row
of the dock's active row container — carrying the option role, its selected state and its row
identity attribute — so the dock keeps exactly one composite widget and one tab stop; where the
narrative choice-point embeds it, the card SHALL stay a natively tab-focusable button. Both forms
SHALL come from that one component, never from a second card renderer. The `known_action` card SHALL
carry its label and optional hint; the `freeform` card SHALL carry its label (the phrase the player
speaks, by contract); the dismiss control SHALL be rendered once per suggestions surface, not per
card, and SHALL appear for both `ready` and `degraded` states — as a row of the pane where the dock
hosts it, and as a separate small button where another surface hosts it. All card text SHALL be rendered as literal text nodes; no content
from a card may ever enter a markup allowlist pipeline.

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

### Requirement: Suggestion cards execute exact envelopes through the action client

Activating a suggestion card or its dismiss control SHALL dispatch through the existing action
client (`window.Elosern.actions.submit`), with no new OOB message type and no envelope change. Where
the dock hosts the card as a row of its suggestions frame, activation SHALL traverse the ordinary
router path every other dock row traverses — the delegated pointer bridge's `[data-item-key]` row
handling, the shared focus, disabled-explanation and submission gates, and the identical keyboard
confirmation — and SHALL still ignore keyboard-synthesized clicks. Where another surface hosts the
card, activation SHALL use the direct click handler on the native button and SHALL NOT involve the
KeyboardRouter. In both cases the dispatched envelopes are exactly:

- `known_action` card → `submit(action_code, params)` with the card's validator-normalized
  payload as-is.
- `freeform` card → `submit("explore.talk_freeform", {"npc_id": params.npc_id,
  "speech": label})` — the speech is always the label text.
- Dismiss control → `submit("options.dismiss", {})`.

A card activation SHALL NOT be echoed as a command line (no display descriptor exists for suggestion
cards — the existing echo bridge stays silent), and a locked action client (offline,
synchronizing, or another mutation in flight) SHALL reject the submit without side effects,
exactly as for every other action. A card hosted outside the dock SHALL remain natively
tab-focusable and pointer-activatable; a card hosted as a dock row SHALL be reachable by the dock's
arrow-key navigation and by pointer, and SHALL NOT be individually reachable by sequential keyboard
navigation, because the dock is one composite widget with a single tab stop.

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

### Requirement: A degraded payload with zero cards renders the defined empty-state

A `degraded` payload carrying an empty card list SHALL render the muted line
"現在沒有什麼值得做的動作" as the suggestions pane's body (never an empty container and never a
failure), alongside the muted unavailability note and the dismiss row.
The v1 exploration derivation always yields at least one rule card, so this state is unreachable
in v1 and exists purely as a safe fallback for future kinds without an idle baseline. A `v5`
payload with a **missing** `suggestions` field is never a valid case (the v5 contract requires
the field in every payload); the view treating it as `unavailable` is only a defensive
compatibility guard for pre-v5 panels or a not-yet-landed mirror, never a normal render path.

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
