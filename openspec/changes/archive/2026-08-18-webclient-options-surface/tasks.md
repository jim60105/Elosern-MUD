## 1. Shared Card Component and View Model

- [x] 1.1 Create `web/static/webclient/js/elosern/option_cards.js`: a single card-builder that
      renders one suggestion card as a native `<button>` element (label + optional hint as literal
      text nodes only, from the validated `kind`, `action_code`, `label`, `params`, `hint` fields)
      and a separate dismiss-button factory for the section corner
- [x] 1.2 Add the DOM-independent `buildOptionsView(panel)` derivation in the same module
      (returns `{status, cards, visible, emptyState}` for the four v5 `suggestions` statuses;
      a missing `suggestions` field maps to `visible: false` as a documented compatibility guard
      only — never a normal v5 render case), with `window.Elosern.OptionCards` exposure
- [x] 1.3 Wire the new module into the Node test environment and the browser plugin regime (no
      new runtime dependencies; follow the existing `module.exports`/`window.Elosern` UMD split)

## 2. Exploration Dock Integration (single owner)

- [x] 2.1 Render the suggestions section inside `exploration_dock.js` `_renderDock` (between the
      menu layout and the live region), reading `state.panels["context_actions"]` (the validated
      v5 panel — the same read the combat dock uses) through `buildOptionsView`; the section is
      present only in exploration mode and torn down by the existing `_unmount` path. No new dock
      plugin writes `#action-dock`
- [x] 2.2 Extend the dock's rebuild signature with a `suggestionsSignature` (status + card count +
       full card content — kind, action code, label, canonical params, hint — from the validated
       panel); a panel update that changes only that signature re-renders the section in place (no
       dock rebuild, no keyboard-router reset), and the `_refresh` menu-only path also re-renders
       the section so it can never go stale
- [x] 2.3 Implement the four status renders: `generating` muted line; `ready` cards with the
      dismiss control; `degraded` cards with the muted "AI 建議目前不可用" note and dismiss;
      `unavailable` renders no section; `degraded` with zero cards renders
      "現在沒有什麼值得做的動作" as the section body
- [x] 2.4 Attach direct `click` handlers to each card/dismiss button (native `<button>` elements;
      Enter/Space keyboard activation works natively) that dispatch exact envelopes through
      `window.Elosern.actions.submit` — `known_action` → `submit(action_code, params)` unchanged;
      `freeform` → `submit("explore.talk_freeform", {npc_id, speech: label})`; dismiss →
      `submit("options.dismiss", {})`; no command echo for any card dispatch; listeners are
      detached on section teardown
- [x] 2.5 Preserve the existing dock ownership rules: combat/creation `data-mode` gating and the
      re-homed services/character sub-dock deferral must be untouched, and the section must never
      render under another mode's dock

## 3. Node Tests

- [x] 3.1 Add `web/static/webclient/js/tests/options_view.test.js`: pure `buildOptionsView`
      coverage for all four statuses, missing-section compatibility guard, card list passthrough,
      and the zero-card `degraded` empty-state
- [x] 3.2 Add `web/static/webclient/js/tests/option_cards.test.js`: card elements carry the exact
      label text and hint as text nodes, `known_action`/`freeform` buttons differ only in payload
      contract, the dismiss button is a separate element, and the suggestion signature derivation
      (status + count + action codes) is asserted

## 4. Browser Verification

- [x] 4.1 Add `web/tests/browser/test_browser_options_surface.py` (one file, one server per test
       class, no combat sessions): moving into a room shows the generating line then ready cards;
       clicking
      a known card executes its action; clicking a freeform card sends `speech = label`; the
      dismiss control hides the dock section; a suggestions-only `ui_update` re-renders the
      section without disturbing the exploration menu; with the LLM profile disabled, degraded
      rule cards render in the dock only with the muted note
- [x] 4.2 Make the browser fixtures deterministic: use the test-only fake-client injection
      (`world/ai/fake_client.py` conventions) with a fixed `OptionSet`, reset the character's
      room and session options state before each test, and wait on the store's
      `context_actions.suggestions.status` (bounded poll, no timing sleeps)
- [x] 4.3 Update the browser-shards contract if the new file changes the serial-owner set (each
      file keeps exactly one owner input to the CI sharding)

## 5. Verification and Compliance

- [x] 5.1 Run the Node suite (`node --test web/static/webclient/js/tests/*.test.js`), the new
      browser test file, and the touched regression tests (`ui_contract`, `protocol`,
      `dock_surface`, exploration dock browser coverage) until green
- [x] 5.2 Run `openspec validate webclient-options-surface --strict` and confirm no player
      command surface changed (`tests/test_command_docs.py` unaffected; `options.dismiss` is an
      OOB action)