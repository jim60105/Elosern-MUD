## 1. Shared Card Component and View Model

- [ ] 1.1 Create `web/static/webclient/js/elosern/option_cards.js`: a single card-builder that
      renders one suggestion card as a native `<button>` element (label + optional hint as literal
      text nodes only, from the validated `kind`, `action_code`, `label`, `params`, `hint` fields)
      and a separate dismiss-button factory for the section corner
- [ ] 1.2 Add the DOM-independent `buildOptionsView(panel)` derivation in the same module
      (returns `{status, cards, visible, emptyState}` for the four v5 `suggestions` statuses,
      treating a missing section as `unavailable`), with `window.Elosern.OptionCards` exposure
- [ ] 1.3 Expose the module for both regimes (follow the existing `module.exports`/
      `window.Elosern` UMD split) so the Node suite and the exploration dock load the same code;
      no new runtime dependencies

## 2. Exploration Dock Integration

- [ ] 2.1 Render the suggestions section inside `exploration_dock.js` `_renderDock` (between the
      menu layout and the live region), reading `panel.suggestions` through `buildOptionsView` —
      section present only in exploration mode, torn down by the existing `_unmount` path
- [ ] 2.2 Implement the four status renders: `generating` muted line; `ready` cards with the
      dismiss control; `degraded` cards with the muted "AI 建議目前不可用" note and dismiss;
      `unavailable` renders no section; `degraded` with zero cards renders
      "現在沒有什麼值得做的動作" as the section body
- [ ] 2.3 Install direct click handlers on the section's native buttons (card and dismiss) that
      call `window.Elosern.actions.submit` and are detached on dock teardown — exact envelopes:
      `known_action` → `submit(action_code, params)` unchanged; `freeform` →
      `submit("explore.talk_freeform", {npc_id, speech: label})`; dismiss →
      `submit("options.dismiss", {})`; no command echo for any card dispatch; no KeyboardRouter
      frames created for the section; no `data-action` bridge involvement
- [ ] 2.4 Extend the dock subscribe handler with a `suggestionsSignature` (status + card count +
      action codes): when only it changes, re-render the section in place without a dock rebuild
      or keyboard reset; the `_refresh` menu-only path must also re-render the section
- [ ] 2.5 Preserve the existing dock ownership rules: combat/creation `data-mode` gating and the
      re-homed services/character sub-dock deferral must be untouched, and the section must never
      render under another mode's dock

## 3. Node Tests

- [ ] 3.1 Add `web/static/webclient/js/tests/options_view.test.js`: pure `buildOptionsView`
      coverage for all four statuses, missing section, card list passthrough, and the zero-card
      `degraded` empty-state
- [ ] 3.2 Add `web/static/webclient/js/tests/option_cards.test.js`: card elements carry the exact
      label text and hint as text nodes, `known_action`/`freeform` buttons differ only in payload
      contract, the dismiss button is a separate element, and activation funnels to the submit
      function
- [ ] 3.3 Add Node coverage for the section's activation paths: pointer click and keyboard
      activation (Enter/Space — keyboard-synthesized clicks are NOT filtered out, unlike the
      `[data-item-key]` pointer bridge) both dispatch the exact envelope, and a locked/submitting
      action client rejects the dispatch every time (no side effects in all failure modes)

## 4. Browser Verification

- [ ] 4.1 Add `web/tests/browser/test_browser_options_surface.py` (one file, shared-server scope,
      no combat sessions): moving into a room shows the generating line then ready cards; clicking
      a known card executes its action; clicking a freeform card sends `speech = label`; the
      dismiss control hides the section in the dock; with the LLM profile disabled, degraded rule
      cards render in the dock and the muted note shows. Use the test-only fake-client injection
      for fixed `OptionSet`s (no live LLM), reset the character's room/options state before each
      test (fresh character or state reset helper), and wait deterministically on the store's
      `context_actions.suggestions.status` (poll with a bounded deadline) rather than timing
      sleeps
- [ ] 4.2 Update the browser-shards contract if the new file changes the serial-owner set (each
      file keeps exactly one owner input to the CI sharding)

## 5. Verification and Compliance

- [ ] 5.1 Run the Node suite (`node --test web/static/webclient/js/tests/*.test.js`), the new
      browser test file, and the touched regression tests (`ui_contract`, `protocol`,
      `dock_surface`, exploration dock browser coverage) until green
- [ ] 5.2 Run `openspec validate webclient-options-surface --strict` and confirm no player
      command surface changed (`tests/test_command_docs.py` unaffected; `options.dismiss` is an
      OOB action)