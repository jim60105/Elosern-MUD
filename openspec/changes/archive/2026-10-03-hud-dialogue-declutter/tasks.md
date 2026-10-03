# hud-dialogue-declutter — Tasks

## 1. Add dialogue-mode hide rules

- [x] 1.1 In `HudFrame.vue`, add CSS rules to hide the `vitals` and `map` anchors in dialogue mode:
  ```css
  .elosern-stage[data-elosern-mode="dialogue"] [data-anchor="vitals"],
  .elosern-stage[data-elosern-mode="dialogue"] [data-anchor="map"] {
    display: none !important;
  }
  ```
  Place these alongside the existing creation-mode and combat-mode hide rules in the mode-gated visibility block.
  A live entry may fade over the existing reveal duration with discrete `display` transitions; anchors are inert and `aria-hidden` at commit and settle at `display:none`. Forward mode-gated effective visibility to the real dock so its existing reveal restores it on exit.
- [x] 1.2 Mirror the same rules in `app-shell.css` if that file repeats anchor mode-hide selectors (keep the two files in step).

## 2. Verify focus rescue

- [x] 2.1 Extend `AppShell.vue`'s `HIDDEN_BY_MODE.dialogue` from `[data-anchor='band-command']` to `[data-anchor='band-command'], [data-anchor='vitals'], [data-anchor='map']` and use that selector in the entering-dialogue pre-flush rescue branch (the pre-flush check runs against the still-rendered DOM, so `active.closest(...)` still matches the not-yet-hidden anchors). Do NOT rely on the post-flush `focusIsLost` heuristic — the file's own comment says a browser may not have blurred yet, and a focus held on a minimap node or condition icon must be rescued deterministically.
- [x] 2.2 Test: focus a minimap node, then commit mode `dialogue` → focus lands on the message window's focus target before the anchors are hidden, and no focus is lost to the document body.

## 3. Tests

- [x] 3.1 Update `scene_transitions.test.js` or mode-visibility tests: assert that in dialogue mode, `[data-anchor="vitals"]` and `[data-anchor="map"]` have `display: none`.
- [x] 3.2 Update any managed browser-test file that navigates to a dialogue and expects the vitals dock or minimap to be visible — change the assertion to expect them hidden. Edit the assertions here; execution of the managed browser suite is CI-owned.
- [x] 3.3 Add a focused test: enter dialogue mode with a vital below maximum → vitals dock is hidden (the vitals rule does not override the mode hide).
- [x] 3.4 Add a focused test: exit dialogue mode back to exploration with a vital below maximum → vitals dock reappears.

## 3b. Storybook

- [x] 3.5 Update `HudFrame.stories.js`: the `DialogueStage` / `DialogueCommandLine` / `DialogueEnter` stories render the frame at `mode: "dialogue"` — confirm the built showcase shows the vitals dock and map anchor hidden there (if the story passes real content rather than sample blocks, the CSS hide already applies; if a sample-block label implies visibility, adjust the label to note the dialogue declutter). No new story needed if the existing dialogue stories demonstrate the hide.

## 4. Verify

- [x] 4.1 Run the focused Vitest tests (`pnpm test` scoped to the touched test files) and the Node gate (`node --test web/static/webclient/js/tests/*.test.js`, fast per AGENTS.md). No full-suite runs.
- [x] 4.2 Visual smoke: enter dialogue → vitals dock and map anchor hidden; exit dialogue → restored.
- [x] 4.3 `openspec validate hud-dialogue-declutter --strict` passes.
- [x] 4.4 Run `uv run --locked python -m tools.contract_gate` (seconds; traceability + lints + shard manifests — not a test run; required before handoff).
- [x] 4.5 Run the Storybook gates: `pnpm run build-storybook` and `pnpm run showcase-coverage` (no component set change; the built dialogue stories must show the decluttered stage — vitals dock and minimap island gone under `mode="dialogue"`).

### Verification evidence

- Focused Vitest: `hud_frame.test.js`, `scene_transitions.test.js`, and `data/vitals_visibility.test.js`: 56 tests passed. The minimap-node/condition-control focus spies observe the old exploration DOM at the rescue call. Real AppClient revisions suppress injured vitals during dialogue and apply the existing positive-travel reveal on exit.
- Node gate: 479 passed. Storybook build passed; showcase coverage: 62/62 required components.
- Strict change validation passed; traceability: 1828/1828 covered, no errors; contract gate passed including all 18 contracts. `git diff --check` passed.
- agent-browser: inspected selector, companion-speaking, full-party and frame dialogue screenshots at 1920×1080 and 1280×720; manually stepped mode journey talk → leave at both sizes. Live entry sampled opacity between zero and one while inert, then both anchors settled at `display:none`; exit restored both to `display:flex`, opacity one and non-inert. Motion-off hid both on the first animation frame.
- Built showcase: DialogueStage, DialogueCommandLine and the dialogue phase of DialogueEnter each report both anchors `display:none`. Managed browser assertion updates are CI-executed only.
- Artifact reconciliation: preserve the existing scenario title “Dialogue mode keeps the cockpit visible” because strict full-superset MODIFIED validation requires it; its assertions concern the surviving conversation surfaces. Requirement headings/traceability IDs remain unchanged; no archive-time annotation re-points are needed.
- Post-implementation review found no blocking issues. Its place-card wording concern was adopted: the card requirement and existing scenario explicitly permit only inert live-entry exit paint, then require the hidden settled state.
