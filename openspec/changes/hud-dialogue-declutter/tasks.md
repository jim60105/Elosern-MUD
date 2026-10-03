# hud-dialogue-declutter — Tasks

## 1. Add dialogue-mode hide rules

- [ ] 1.1 In `HudFrame.vue`, add CSS rules to hide the `vitals` and `map` anchors in dialogue mode:
  ```css
  .elosern-stage[data-elosern-mode="dialogue"] [data-anchor="vitals"],
  .elosern-stage[data-elosern-mode="dialogue"] [data-anchor="map"] {
    display: none !important;
  }
  ```
  Place these alongside the existing creation-mode and combat-mode hide rules in the mode-gated visibility block.
- [ ] 1.2 Mirror the same rules in `app-shell.css` if that file repeats anchor mode-hide selectors (keep the two files in step).

## 2. Verify focus rescue

- [ ] 2.1 Extend `AppShell.vue`'s `HIDDEN_BY_MODE.dialogue` from `[data-anchor='band-command']` to `[data-anchor='band-command'], [data-anchor='vitals'], [data-anchor='map']` and use that selector in the entering-dialogue pre-flush rescue branch (the pre-flush check runs against the still-rendered DOM, so `active.closest(...)` still matches the not-yet-hidden anchors). Do NOT rely on the post-flush `focusIsLost` heuristic — the file's own comment says a browser may not have blurred yet, and a focus held on a minimap node or condition icon must be rescued deterministically.
- [ ] 2.2 Test: focus a minimap node, then commit mode `dialogue` → focus lands on the message window's focus target before the anchors are hidden, and no focus is lost to the document body.

## 3. Tests

- [ ] 3.1 Update `scene_transitions.test.js` or mode-visibility tests: assert that in dialogue mode, `[data-anchor="vitals"]` and `[data-anchor="map"]` have `display: none`.
- [ ] 3.2 Update any browser journey that navigates to a dialogue and expects the vitals dock or minimap to be visible — change the assertion to expect them hidden.
- [ ] 3.3 Add a focused test: enter dialogue mode with a vital below maximum → vitals dock is hidden (the vitals rule does not override the mode hide).
- [ ] 3.4 Add a focused test: exit dialogue mode back to exploration with a vital below maximum → vitals dock reappears.

## 4. Verify

- [ ] 4.1 Run focused Vitest (`pnpm test` on touched files) and Node gate.
- [ ] 4.2 Visual smoke: enter dialogue → vitals dock and map anchor hidden; exit dialogue → restored.
- [ ] 4.3 `openspec validate hud-dialogue-declutter --strict` passes.
