## Context

The `context_actions` v5 panel (delivered by the preceding `context-actions-suggestions` slice; version
sequence recorded in the affordance-contract proposal — v4 carries the exploration form, v5 adds
`suggestions`) already reaches the store, validated by the `protocol.js` mirror. Nothing renders
`suggestions` yet: in exploration mode the `#action-dock` surface is owned by
`web/static/webclient/js/plugins/exploration_dock.js`, which rebuilds the whole dock (wipe +
recreate) on every state change, reserves the dock for combat/creation via `data-mode`, and defers
to the re-homed services/character sub-docks while active. The combat dock owns `#action-dock` in
combat mode and reads `state.panels["context_actions"]` directly
(`web/static/webclient/js/plugins/combat_dock.js`). The action client
(`web/static/webclient/js/plugins/elosern_actions.js`) submits exact `ui_action` envelopes with
one in-flight lock; pointers are handled by one delegated `mousedown` bridge on the stable
`#action-dock` element (`dock_surface.js`), and `#elosern-action-live` is the stable live region
for notices.

The trigger-service slice publishes `suggestions` transitions (`generating` → `ready` /
`degraded`, `unavailable` on dismiss/initial) as `ui_update` panel replacements; the dismiss OOB
action (`options.dismiss`, payload `{}`) lands with the unified three-parameter adapter ABI. The
narrative-stream choice-points belong to the later `webclient-options-choicepoints` slice, which
reuses the card component this change delivers.

## Goals / Non-Goals

**Goals:**
- Render the `suggestions` section inside the exploration dock with the four status renders
  (`generating` one muted line; `ready` 3–5 clickable cards + dismiss; `degraded` rule cards +
  muted note + dismiss, 0-card empty-state line as a safe fallback; `unavailable` hidden).
- One shared card DOM component (`option_cards`) that the later narrative choice-point slice
  reuses unchanged — same element, same click paths, same data sources.
- Execute cards through the existing action client with exact envelopes: `known_action` →
  `submit(action_code, params)`; `freeform` → `submit("explore.talk_freeform", {npc_id,
  speech: label})`; dismiss → `submit("options.dismiss", {})`.
- Keep the dock DOM single-owner: no second writer to `#action-dock`, no new subscription
  machinery, no new OOB message types, no `protocol.js` changes (the v5 mirror belongs to the
  panel slice).
- Add a Node suite for the DOM-independent view model and one shared-server Playwright file.

**Non-Goals:**
- Narrative-stream choice-points (change 10).
- Any keyboard-router integration for the suggestion cards (they are direct pointer surfaces;
  the dock menu keeps router ownership).
- Re-validating panel data client-side (already guaranteed by the mirror at `commitPresentation`).
- Any server, protocol, or command change; `docs/game/commands.md` is untouched.
- Dismiss keyboard shortcut, card reordering, analytics, or per-player personalization.

## Decisions

### D1: The exploration dock owns the suggestions section (no second `#action-dock` writer)

The section is built **inside** `exploration_dock.js`'s `_renderDock` layout (between the menu
layout and the live region), rendered from the **`context_actions` v5 panel** (the same
`state.panels["context_actions"]` read the combat dock uses; its `suggestions` carries the
status/cards the section shows) alongside the `exploration` panel the dock already consumes.
Rationale over alternatives:

- A separate plugin subscribing to the controller and appending its own subtree would race the
  dock's full wipe-and-rebuild on every state change (two writers on one DOM tree).
- A dock-level "stable appended block" would be annihilated by `_renderDock`; re-mounting after
  each rebuild re-introduces the race.
- Building inside the dock reuses the existing mode gating (`data-mode`), the services/character
  sub-dock deferral, and the tree teardown on mode exit for free: when the dock unloads
  (`_unmount`), the section leaves with it; combat/creation never see it.

**Update trigger (review fix):** the dock's subscribe handler today rebuilds only when the
`exploration` panel signature (or epoch) changes — suggestions updates (`generating` → `ready`,
dismiss → `unavailable`) do not move that signature. The handler SHALL additionally derive a
small `suggestionsSignature` from the validated `context_actions` panel (status + card count +
card action codes, not the full card list), and when only that signature changes, re-render the
section in place **without** rebuilding the dock or resetting the keyboard router. The `_refresh`
partial path (which re-renders only menu rows when `.exploration-menu` exists) SHALL also
re-render the section, so a stale section can never survive a menu-only refresh.

The section's state derivation is extracted as a DOM-independent pure function
`buildOptionsView(panel) → {status, cards, visible, emptyState}` in the same new module so the
Node suite can exercise every status without DOM.

### D2: One shared card component in `option_cards.js`

New `web/static/webclient/js/elosern/option_cards.js` exposes a single card-builder returning
plain DOM (native `<button>` elements, text via text nodes — never innerHTML) given a validated
card (`kind`, `action_code`, `label`, `params`, optional `hint`) and a click handler factory:

- `known_action` card button; narrow hint line under the label when present.
- `freeform` card button (the label is the phrase the player speaks, by contract).
- A "✕ 清除建議" dismiss button rendered by the *section*, not by each card.

The dock embeds these elements; change 10 embeds the same builder into the narrative stream, so
size, labels, and click paths cannot diverge between surfaces.

### D3: Execution through the existing action client, no echo

Card clicks resolve to `window.Elosern.actions.submit(...)`:

- `known_action` → `submit(card.action_code, card.params)`; the validator-normalized `params` are
  the payload by contract (schema stage 9 guarantee).
- `freeform` → `submit("explore.talk_freeform", {npc_id: params.npc_id, speech: label})`.
- Dismiss → `submit("options.dismiss", {})`.

No display descriptor is passed (cards carry none), so the `CommandEcho` bridge resolves to null
and stays silent — matching the existing D4 echo semantics, and avoided deliberately: a
suggestion card is a click surface, not a typed command.

### D4: Direct click handlers on native buttons — no pointer-bridge involvement

Review verified the delegated pointer bridge (`DockSurface.installPointerBridge`) matches only
`[data-item-key]` elements, routes through `KeyboardRouter.confirm`, and deliberately ignores
keyboard-synthesized clicks (`detail === 0`) — it cannot drive suggestion cards. The section
therefore installs **a direct `click` listener per suggestion/dismiss button** (owning its
subscriptions and detaching them on dock teardown); native `<button>` elements give keyboard
activation (Enter/Space) for free, and every path funnels into the same D3 submission function.
No `data-action` attributes, no bridge changes, no KeyboardRouter frames — the router stays the
exclusive owner of the exploration menu stack. A dismissed/`unavailable` section renders nothing
(no placeholder), so no stale listener or focus residue survives. Node and browser tests cover
pointer activation, keyboard activation, and the locked-submit path.

### D5: Suggestions updates re-render the section only — the dock rebuild is not required

A `suggestions` change arrives as a `ui_update`/snapshot panel replacement. When only the
`suggestions` content moved, the section re-renders in place (D1's signature split); when the
`exploration` panel itself changed, the existing full `_renderDock` rebuild recreates the section
as part of the subtree. On the service side a repeated `generating` status publishes no new panel
update; on the client side any dock rebuild that does happen recreates an equivalent muted line —
there is no promise of DOM identity across rebuilds (review wording fix). `ready`/`degraded`
replace the line in place; `unavailable` omits the section entirely.

### D6: Degraded empty-state is a defined fallback, not an expectation

The mirror accepts `degraded` with 0 cards (a future baseline-less kind); v1 exploration always
yields ≥ 1 rule card (the idle baseline). The section renders the muted line
"現在沒有什麼值得做的動作" for the 0-card case so a legal-but-unexpected payload can never render
an empty gray box; the "AI 建議目前不可用" note accompanies any `degraded` render. A **missing**
`suggestions` field is never a valid v5 case (the v5 contract requires it in every payload); the
view treats it as `unavailable` only as a defensive compatibility guard against pre-v5 panels or
a not-yet-landed mirror, and the v5 fixtures assert the mirror rejects a payload without the
field (the panel slice's own parity suite; this slice's Node tests cover the guard only).

### D7: Test split — pure Node + browser integration

- `option_cards.js` (DOM construction with injected document) and `buildOptionsView` (pure) are
  covered by `web/static/webclient/js/tests/option_cards.test.js` + `options_view.test.js` with
  the existing Node conventions (DOM stubs where isolated).
- Dock integration (four status renders, pointer + keyboard activation → exact envelopes, dismiss
  hides the section, suggestions-only updates re-render the section without a dock rebuild, mode
  gating vs combat/creation, LLM-off degraded path) is covered by one Playwright file
  `web/tests/browser/test_browser_options_surface.py` booting a **shared server** (the repo rule:
  each browser file has one serial owner; no combat sessions are started, so shared-server reuse
  applies).
- **Deterministic browser fixtures (review fix):** the ready/degraded paths need a fixed `OptionSet`
  without any live LLM. Each test uses the test-only fake-client injection the layer already
  provides (`world/ai/fake_client.py` conventions), resets the character's room/session options
  state before each test, and waits on the store's `context_actions.suggestions.status` (poll
  until a bounded deadline) instead of timing sleeps, so generating→ready transitions and card
  clicks are asserted against a known payload.

## Risks / Trade-offs

- **Exploration dock rebuild footprint** → The section is one bounded subtree assembled from the
  already-validated panel; the dock already rebuilds wholesale on every state change, so the
  added cost is one subtree build per render.
- **v5 mirror not yet landed** → This change is sequenced after the panel slice; until it lands,
  no `suggestions` data reaches the store (mirror rejection), and the dock naturally renders
  without the section. Degradation path: the section simply never appears.
- **Click surface vs router focus** → Suggestion cards cannot be activated by the arrow-key
  router; this is a deliberate v1 scope cut (the deck is a pointer convenience), recorded in the
  Non-Goals, with native tab focus retained.
- **Card labels are freeform text** → Labels are constrained by the mirror (≤ 24 chars, CJK, no
  digits/placeholders) and always rendered as literal text nodes; no markup pipeline is used,
  matching the narrative-input input-line rule.

## Migrations

The project has no released users; no backward-compatibility layer is added. The section is
opt-in client rendering that appears only when a v5 `suggestions` field is present; older cached
panels simply render without a section.

## Open Questions

- None blocking. Whether the choice-point should later also accept `degraded` cards is deferred
  to the choice-point slice (recorded there as a one-line reversal).