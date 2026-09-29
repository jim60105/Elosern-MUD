## 1. Implement the bounded surface

- [x] 1.1 Apply seam, divider and shared control-strip geometry; inspect exploration/dialogue/combat with captions and expanded command line.
- [x] 1.2 Make popover opaque and remove only its duplicate heading; exercise back/escape and disabled actions without dispatch leakage.
- [x] 1.3 Simplify container/command-line focus and style the existing secondary footer buttons; walk keyboard focus on the live client.
- [x] 1.4 Replace the panel flip with motion-token variants; inspect full/reduced/off without pinning CSS source.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-band-material-pass --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.

## Verification record

- Vitest: `pnpm test` → 124 files, 1371 tests passed (includes the literal-duration guard); new `tests/action/action_dock.test.js` case pins the popover-only breadcrumb exemption.
- Browser (local, one file/class each): `web.tests.browser.test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_breadcrumb_tracks_router_depth` (rewritten popover half), `test_browser_mode_transitions` combat/dialogue full-motion cases, `test_browser_shell_dock` (seam assertions replace the retired `border-top` pin), `test_vue_typography`, `test_browser_pointer`, `test_browser_contextual_hud_anchors`, `test_browser_exploration_dialogue`, `test_browser_input_narrative.InputEchoExplorationTest.test_message_window_pages_and_flushes` → all OK.
- Storybook via agent-browser at 1920x1080 and 1280x720: PopulatedHud (+ `/` command line), VerbPopoverSelector, WaitingSelector, DialogueSelector, CombatParticipantPolish. Observed: opaque popover with one heading and no crumb; one command-field focus frame with centred text; secondary footer buttons; legend and 日誌 / ⌨ on one baseline (pane ends at the strip, legend no longer overpainted); feather clears the dialogue choices, scene caption and foe plates at 1280x720.
- Motion (ModeJourney, sampled computed style every 30ms): full → `elosern-panel-flip-in` 250ms, translateX -14px→0 with a closing clip wipe; reduced (emulated `prefers-reduced-motion`) → 150ms opacity only, transform identity, clip inset fully open; off → 0ms token (browser suite default).
