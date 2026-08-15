## ADDED Requirements

### Requirement: The exploration dock renders the suggestions section from the validated v5 panel

In exploration mode the action-dock surface SHALL render a `suggestions` section derived from the
`context_actions` panel the store already validated (mirror-accepted at commit time), with exactly
one of four renders:

- `status = "generating"`: one muted line "AI 正在構思建議…", no cards, no dismiss control.
- `status = "ready"`: the section SHALL show between 3 and 5 clickable suggestion cards (the
  bound the server validator enforces for ready sets), each with its label and optional hint, and
  a "✕ 清除建議" dismiss control at the section corner.
- `status = "degraded"`: the section SHALL show rule cards (0–5; the v1 exploration derivation
  always yields ≥ 1) plus one muted "AI 建議目前不可用" note and the same dismiss control.
- `status = "unavailable"`: the section SHALL render nothing at all.

The section SHALL appear only while the exploration dock owns the surface (never in combat or
creation mode, and never while a re-homed services/character sub-dock is active), SHALL be torn
down with the dock on mode exit, and SHALL derive its status, card list, and visibility through a
DOM-independent view function so every status is testable without a browser. A panel update that
changes only the suggestions content SHALL re-render the section without rebuilding the dock or
resetting the keyboard router. Repeated `generating` statuses are never separately published by
the trigger service; any dock rebuild that does occur SHALL render an equivalent generating line
(no DOM-identity promise across rebuilds). All text SHALL be rendered as literal text nodes —
never through an HTML/markup pipeline.

#### Scenario: The section follows the four statuses
- **WHEN** a puppeted WebClient in exploration mode presents `suggestions` with status
  `generating`, then `ready` (3–5 cards), then `degraded` (rule cards), then `unavailable`
- **THEN** the dock first shows the muted generating line, then the ready card set with the
  dismiss control, then the degraded rule cards with the muted note and dismiss control, and
  finally no section at all

#### Scenario: The section never appears in combat or creation mode
- **WHEN** the active mode is combat or character creation while the same `context_actions`
  panel streams `suggestions`
- **THEN** the dock surface shows no suggestions section, and returning to exploration mode
  without an available panel also renders none

### Requirement: One shared card component renders every suggestion card

A single card component SHALL build every suggestion card as native `<button>` elements from the
validated card fields (`kind`, `action_code`, `label`, `params`, optional `hint`) — the same
component the dock embeds and the later narrative choice-point slice reuses, so both surfaces
cannot diverge. The `known_action` card SHALL carry its label and optional hint; the `freeform`
card SHALL carry its label (the phrase the player speaks, by contract); the dismiss control SHALL
be a separate small button rendered once per section, not per card, and SHALL appear for both
`ready` and `degraded` states. All card text SHALL be rendered as literal text nodes; no content
from a card may ever enter a markup allowlist pipeline.

#### Scenario: The dock and the choice-point surface share one builder
- **WHEN** a `known_action` card and a `freeform` card with hint are rendered by the component
- **THEN** each produces a button with the exact label text, the hint rendered as a plain text
  line where present, and the same click contract, and the dismiss control is separate from both

### Requirement: Suggestion cards execute exact envelopes through the action client

Activating a suggestion card or its dismiss control SHALL dispatch through the existing action
client (`window.Elosern.actions.submit`) via direct click handlers on the native buttons (the
delegated pointer bridge drives only `[data-item-key]` router rows and ignores
keyboard-synthesized clicks, so it never carries cards), with no new OOB message type and no
KeyboardRouter involvement:

- `known_action` card → `submit(action_code, params)` with the card's validator-normalized
  payload as-is.
- `freeform` card → `submit("explore.talk_freeform", {"npc_id": params.npc_id,
  "speech": label})` — the speech is always the label text.
- Dismiss control → `submit("options.dismiss", {})`.

A card click SHALL NOT be echoed as a command line (no display descriptor exists for suggestion
cards — the existing echo bridge stays silent), and a locked action client (offline,
synchronizing, or another mutation in flight) SHALL reject the submit without side effects,
exactly as for every other action. The buttons SHALL remain natively tab-focusable and
pointer-activatable.

#### Scenario: Clicking a ready card dispatches its exact envelope
- **WHEN** the player clicks a `known_action` card (`"explore.move"` with
  `{exit_ref, current_node}`) and then clicks a `freeform` card for NPC 7 labeled
  "我們聊聊好嗎？"
- **THEN** the client submits `ui_action` envelopes for `explore.move` with the card's payload
  unchanged and for `explore.talk_freeform` with `{npc_id: 7, speech: "我們聊聊好嗎？"}`, and
  neither dispatch echoes a command line

#### Scenario: The dismiss control hides the section
- **WHEN** the player clicks "✕ 清除建議" while the section shows `ready` or `degraded` cards
- **THEN** the client submits `options.dismiss` with an empty payload, and once the published
  `unavailable` state arrives, the section disappears from the dock

### Requirement: A degraded payload with zero cards renders the defined empty-state

A `degraded` payload carrying an empty card list SHALL render the muted line
"現在沒有什麼值得做的動作" as the section body (never an empty container and never a failure).
The v1 exploration derivation always yields at least one rule card, so this state is unreachable
in v1 and exists purely as a safe fallback for future kinds without an idle baseline.

#### Scenario: Zero-card degraded renders the empty-state line
- **WHEN** the store presents a `degraded` suggestions payload with an empty `cards` array
- **THEN** the section body shows "現在沒有什麼值得做的動作" together with the "AI 建議目前
  不可用" note and the dismiss control, and no crash or empty box is rendered