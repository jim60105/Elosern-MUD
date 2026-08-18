## Why

The `context_actions` v5 panel (landed by the preceding opener slice — OpenSpec change
`context-actions-suggestions`, which bumps the panel from the v4 exploration form to v5 with
`suggestions`, per the version sequence recorded in the affordance-contract proposal) carries the
`suggestions` section — AI `ready` cards, rule `degraded` cards, and the transient `generating`
state — but nothing in the WebClient renders it yet. The player sees text only; the curated "what
now?" card row, the whole product difference of the action-options feature, has no usable surface.
This change delivers the stable dock surface and the one shared card component that the later
narrative choice-point slice reuses.

## What Changes

- New DOM-independent card model + renderer in `web/static/webclient/js/elosern/option_cards.js`:
  one card renderer used by the dock and (later) the narrative stream, rendering `known_action`
  and `freeform` cards from validated panel data only — `action_code`, `label`, `params`, optional
  `hint`, plus a separate dismiss-button factory; no unmirrored field is ever read.
- The exploration dock (`web/static/webclient/js/plugins/exploration_dock.js`) — the **single
  writer** of `#action-dock` in exploration mode — gains a suggestions section built inside its
  `_renderDock` layout and fed from `state.panels["context_actions"]` (the same validated read the
  combat dock uses). No new dock plugin writes the dock surface; the section is torn down by the
  existing dock `_unmount`, and combat/creation never see it:
  - `generating`: one muted line "AI 正在構思建議…" (no skeleton cards).
  - `ready`: 3–5 card buttons (label + optional hint) and a "✕ 清除建議" dismiss control.
  - `degraded`: rule cards + one muted "AI 建議目前不可用" note, same dismiss control; a 0-card
    payload renders the empty-state line "現在沒有什麼值得做的動作" (a safe fallback — v1
    exploration always yields ≥ 1 rule card).
  - `unavailable`: the section is hidden entirely (initial state, after dismiss, combat/creation
    mode, and when no kind applies).
  - A `suggestions`-only update re-renders the section in place without a dock rebuild or
    keyboard-router reset (the dock's rebuild signature gains a suggestions digest; the `_refresh`
    menu-only path also re-renders the section).
- Execution paths through the existing action client (`window.Elosern.actions.submit`), installed
  as **direct click handlers on native buttons** (the delegated pointer bridge only drives
  `[data-item-key]` router rows and ignores keyboard-synthesized clicks, so it cannot carry
  cards); Enter/Space keyboard activation works natively; no new message types:
  - `known_action` card → `submit(action_code, params)` with the card's validator-normalized
    payload.
  - `freeform` card → `submit("explore.talk_freeform", {npc_id: params.npc_id, speech: label})` —
    the speech is always the label text, by contract.
  - Dismiss control → `submit("options.dismiss", {})`.
- The section renders only from already-validated store state: the client mirror accepted the v5
  panel in `commitPresentation` before the store ever exposes it; a missing `suggestions` field
  is only a defensive compatibility guard (never a valid v5 render case).
- Node tests for the card model/renderer and the dock-section view model, plus one Playwright
  test file booting a single per-class server (no combat sessions, so one server is safe and each
  journey resets the character through the superuser `@tel` command): move into a room →
  generating line → ready cards; clicking a known card executes; a freeform card sends its
  speech; dismiss hides the dock section; LLM-off shows degraded cards in the dock only. Browser
  fixtures use the deterministic fake-client injection (no live LLM), reset the character's
  room/options state per test, and wait on the store's
  `context_actions.suggestions.status` rather than timing sleeps.

## Capabilities

### New Capabilities
- `webclient-options-surface`: the dock suggestions surface — the four status renders, the shared
  card component (`known_action` / `freeform` / hint / dismiss), the exact execution envelopes,
  and the exploration-mode ownership rules that keep the dock from colliding with combat/creation.

### Modified Capabilities
- None: this slice adds a client surface only. The `context_actions` v5 panel contract, the
  dismiss OOB action, and the trigger-service semantics belong to earlier slices; the narrative
  choice-point stream integration belongs to the later `webclient-options-choicepoints` slice.

## Impact

- **Code**: `web/static/webclient/js/elosern/option_cards.js` (new shared card builder + view
  model), `web/static/webclient/js/plugins/exploration_dock.js` (suggestions section within the
  existing single-owner dock; no new dock plugin), `web/static/webclient/js/tests/
  option_cards.test.js` and `options_view.test.js` (new Node suites), `web/tests/browser/
  test_browser_options_surface.py` (new, shared-server Playwright file). No server code, no
  `protocol.js` schema changes (the v5 mirror is part of the panel slice), no player commands
  (`options.dismiss` is an OOB action, so `docs/game/commands.md` /
  `docs/game/command-reference.md` are unaffected).
- **Tests**: Node model/renderer tests with the existing DOM-stub conventions; browser tests in
  one shared-server file per the repo's serial-ownership contract.
- **Downstream**: change 10 (`webclient-options-choicepoints`) reuses `option_cards.js` and the
  section's state derivation; no behavior here changes the narrative stream.