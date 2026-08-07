## 1. Drawer toggle and default-closed state

- [x] 1.1 Rename the KeyboardRouter `/` event `open-drawer` → `toggle-drawer` in
      `web/static/webclient/js/elosern/keyboard_router.js` (the router stays DOM-independent and never
      knows drawer state; `press` still emits on `/`).
- [x] 1.2 Update `web/static/webclient/js/tests/keyboard_router.test.js`: the slash test asserts
      `toggle-drawer`; add a test that pressing `/` twice emits the event twice (the browser decides
      open/close).
- [x] 1.3 In `web/static/webclient/js/plugins/goldenlayout.js` `registerCommandDrawer`: start
      `drawerOpen = false`; build a dedicated entry `<button class="drawer-entry" type="button">` with
      accessible name `指令輸入（/）` and `aria-expanded`; set `data-open="false"` on the drawer root;
      `open()` sets `data-open="true"` + `aria-expanded="true"` before focusing the field and hides the
      entry button; `close()` reverses it.
- [x] 1.4 In `web/static/webclient/css/elosern.css`: add closed-drawer rules — when
      `data-open="false"`, `.prompt` and `.inputfieldwrapper` are hidden and the `.drawer-entry` button
      is visible; when open, the reverse.
- [x] 1.5 In `web/static/webclient/js/plugins/elosern_ui.js` `routeKeyboard`: on `/` outside any
      editable target, if `drawer.isOpen()` → `drawer.close(true)` (restore dock focus), else route
      through `keyboard.handle("/")` (which now emits `toggle-drawer`); keep the editable-focused `/`
      branch untouched (it must stay ordinary text and never close the drawer).
- [x] 1.6 In the same `routeKeyboard` gate and `wireKeyboardRouter` `onEvent`, handle the renamed
      `toggle-drawer` event (replace the `open-drawer` case).

## 2. Command-line catalog (new module)

- [x] 2.1 Create `web/static/webclient/js/elosern/command_echo.js` (UMD, DOM-independent, stateless):
      `commandLine(actionId, payload, display)` returning a bounded display string or `null`, where
      `display` is a bounded descriptor of server-authored labels.
- [x] 2.2 Verify each mapping's spelling against `commands/*.py` before pinning it: exploration
      mappings `explore.look` → `look <目標>|房間`, `explore.talk_scripted` → `talk <NPC> <話題>`,
      `explore.engage` → `engage <目標>`, `explore.wait` daypart/seconds/sleep → `wait <時段>` /
      `rest <秒數>` / `sleep`, and `explore.talk_freeform` → `talk <NPC> <speech>`; movement
      (`explore.move`, local-map move) has NO `move` command — use the exit label as the documented
      action line.
- [x] 2.3 Combat mappings: `combat.cast` → `cast <技能>[=<目標>]` (target token or AREA shorthand from
      the payload), `combat.forfeit` → `combat forfeit`, `combat.flee` → documented fallback from its
      server label (no typed equivalent).
- [x] 2.4 Service/creation mappings: `guild.register`/`guild.quest_accept`/`guild.quest_abandon`/
      `guild.quest_turnin`/`guild.exam_start`, `shop.buy`/`shop.sell` (with quantity), and
      `creation.preset`/`creation.custom`/`creation.activate`/`creation.reset` — each to its canonical
      typed form.
- [x] 2.5 Return `null` for navigation/back/disabled/submenu items, unknown `actionId`s, and any
      descriptor missing a required label; truncate label-derived strings to the bounded maximum; keep
      the module stateless.
- [x] 2.6 Add `web/static/webclient/js/tests/command_echo.test.js` Node tests: one per mapping (exact
      spelling), the `null` cases (navigation, unknown action, missing descriptor label), the
      no-typed-command fallbacks (move/`combat.flee`), and the truncation bound.

## 3. Display descriptors on menu items

- [x] 3.1 In `web/static/webclient/js/elosern/exploration_menu.js`: attach `commandDisplay` to
      mutation items at build time — exit label on move rows, NPC display name + keyword label on
      keyword items, NPC display name on engage and free-form items, daypart/seconds/sleep on wait
      items — using only the validated panel data already held.
- [x] 3.2 In `web/static/webclient/js/elosern/combat_menu.js`: attach `commandDisplay` (skill label)
      to skill items; ensure the AREA confirm path in `elosern_ui.js` composes the shorthand into the
      display before submitting.
- [x] 3.3 In the services/creation docks' item builders, attach `commandDisplay` (item label,
      quantity, preset/custom values) where those docks own the item shape.
- [x] 3.4 For the local-map move path (`submitLocalMapMove` in `goldenlayout.js`), pass the node's
      server label as the display descriptor.

## 4. Narrative input echo and divider

- [x] 4.1 In `web/static/webclient/js/plugins/goldenlayout.js`: add `appendInput(text)` beside
      `appendNarrative` — literal text node only (no markup tokenizer), same scroll-keep + unread
      marker bookkeeping, a `.narrative-divider` hairline before the `.inp` line unless the log has no
      prior lines, and exactly one unread increment per input event.
- [x] 4.2 Expose a `window.Elosern.narrativeInput` facade (e.g. `{ appendInput }`) from the goldenlayout
      plugin so the action client and the drawer share one append path.
- [x] 4.3 In the drawer `send()` path, echo the raw typed text once per deliberate ordinary send; the
      borrowed free-form branch appends nothing itself (ownership moves to the action path, task 4.5).
- [x] 4.4 In `web/static/webclient/js/plugins/elosern_actions.js` `createBrowserActions`: add an
      optional `echo(text)` callback and have `submit(actionId, payload, display)` invoke it exactly
      when `client.submit()` returns a request id.
- [x] 4.5 In `web/static/webclient/js/plugins/exploration_dock.js` `consumeFreeformText`: resolve the
      display line via `commandLine("explore.talk_freeform", payload, display)`; submit it; return the
      request id and only clear the field / close the drawer / report success when it dispatched; when
      locked, keep the typed speech and the drawer open and return `false`.
- [x] 4.6 Update every submit call site to pass its `commandDisplay` through `actions.submit`:
      `exploration_dock.js` (menu actions via `handleItem`, rest form via `_bindRestKeys`),
      `services_dock.js` (buy/sell quantity), `creation_dock.js` (preset/custom/activate/reset),
      `elosern_ui.js` (combat general items and AREA confirm), and `goldenlayout.js` (local-map move).
- [x] 4.7 In `web/static/webclient/js/plugins/elosern_ui.js` `wireActions`, bind `echo` to
      `window.Elosern.narrativeInput.appendInput`.
- [x] 4.8 In `web/static/webclient/css/elosern.css`: add `.narrative-divider` (1px `--elm-border-dim`
      hairline with vertical margins) and confirm `.inp` lines use the mono face with a subtle left
      accent.

## 5. Browser acceptance

- [x] 5.1 Add `web/tests/browser/test_browser_input_narrative.py` covering: drawer closed on fresh
      mount (input row hidden, entry button visible with `aria-expanded="false"`), entry-button click
      opens+focuses, `/` toggles open/close and restores dock focus, `/` while the field (and another
      editable control) is focused types a literal slash and never closes, typed command echoes one
      `.inp` line with a preceding `.narrative-divider`, a button action (`explore.move`) echoes its
      line with a divider, free-form echoes exactly one line at dispatch, offline/in-flight sends do
      not echo and a locked borrowed send keeps the speech, scrolled-away input keeps `scrollTop` and
      increments the unread marker by exactly one, and the first log line has no divider.
- [x] 5.2 Assert a `combat.cast` echo does not alter the `ui_action` envelope (payload byte-identical
      with and without the echo) and that a label-derived line containing markup-looking characters is
      rendered as literal text (no element created).
- [x] 5.3 Update existing browser suites that assume an always-open drawer:
      `test_browser_shell.py` (`assert_surfaces_visible` must assert the field exists but the wrapper
      is hidden by default; the three tests that click `#inputfield` directly must activate the entry
      button; any drawer geometry test must open the drawer first), plus drawer steps in
      `test_browser_pointer.py`, `test_browser_exploration.py`, `test_browser_combat*.py`,
      `test_browser_services.py`, `test_browser_creation.py`, and `test_browser_layout.py`. Grep the
      repo for every `#inputfield` interaction and adjust.
- [x] 5.4 Wire the new browser test file into the managed browser discovery and run the focused file
      once.

## 6. Verification

- [x] 6.1 Run the Node unit suites: `node --test web/static/webclient/js/tests/*.test.js`.
- [x] 6.2 Run the affected Evennia/browser tests and the full regression domains per the AGENTS.md
      test budget (browser suite last; use the focused files while iterating).
- [x] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and add
      `@covers_requirement` annotations on the discoverable test methods, mapping each new
      main-requirement scenario to its substantively matching test (drawer toggle, field-safe slash,
      default-closed + entry button, borrowed-send dispatch gating, input echo + divider, unread
      increment, catalog resolution, no-echo-on-locked, no double echo, literal rendering).
- [x] 6.4 Run `openspec validate webclient-input-narrative --strict`, keep `git diff --check` clean,
      and confirm no Python/server/panel changes were introduced.