## 1. Implement the bounded surface

- [x] 1.1 Apply prose typography to rendered and measurement surfaces together; exercise punctuation, mixed scripts, long paragraphs and ASCII-map exceptions.
- [x] 1.2 Reposition marker and name underline without changing reader gates; verify typing and auto-beat playback still suppress the marker.
- [x] 1.3 Update dialogue opening highlight and visual ornaments; test disabled-first, all-disabled and pointer-to-keyboard transitions without unintended dispatch.
- [x] 1.4 Observe actual browser paging at all three acceptance sizes, prose scales and reduced/off; retain a regression only for measurement/reading boundary behavior.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-message-typesetting --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.

## Verification record

- Vitest: `pnpm test` — 124 files, 1374 tests passed; `pnpm run showcase-coverage` — 58/58 components and story titles listed.
- Focused browser (local, one command per batch, each well under ten minutes):
  - `test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_prose_typesetting_follows_the_measured_column` (new; 1920x1080, 1440x900, 1280x720 at prose scale 1 and 1.12, exploration and dialogue, reduced and off) and `.test_narrative_caption_bounded_full_log_one_action` — OK.
  - `test_browser_exploration_dialogue.ExplorationBrowserTest.test_pointer_opened_choices_highlight_the_first_choice_without_answering` (new), `.test_dialogue_stage_collapses_the_band_and_stands_both_actors`, `.test_dialogue_choices_sit_over_the_stage_and_the_dock_collapses`, `.test_dialogue_stage_journey_completes_by_keyboard` — OK.
  - `test_browser_input_narrative.DrawerNarrativeBrowserTest` typing, reduced-motion paging, resize re-page, prose scale, and the three motion-level tests — OK (7).
  - `test_browser_shell_command_line.ShellAcceptanceTest.test_paging_marker_and_append_keep_page`, `.test_page_surface_keyboard_advance_and_dock_isolation`; `test_browser_mode_transitions.ModeTransitionsBrowserTest` dialogue full, choice stagger, reduced, off — OK (6).
  - `test_vue_typography` against a freshly rebuilt `.storybook-out` — OK (3).
- Visual smoke (agent-browser, Storybook): `Core/AppShell/DialogueSelector` at 1920x1080 and 1280x720 (marker under the dialogue column's edge at x≈1291 instead of ≈1804, name-aligned underline with lozenge, corner brackets, seal cross badge, quiet unfocused highlight after blur); `Core/AppShell/PopulatedHud` at 1280x720 and 1440x900; `Core/MessageWindow/MorePages` (exploration marker clamped at 104px from the region edge), `MixedScripts` (CJK–Latin autospace visible, map grid intact), `NarrativeTones`. Marker computed style: full `1.6s infinite`, mid-cycle translateY ≈ 2px; reduced and off `0s`, no transform, opacity 1.
- The exits-view scenario ("A disabled first exit is skipped", and the all-disabled case) is covered by the component tests in `tests/dialogue_choices.test.js`; the browser fixture's dialogue room has no disabled exit, and the logic is local to `DialogueChoices`.
- Post-implementation review: the reduced/off marker check now runs on a `more` marker after asserting the 1.6s full-motion bob, the exploration marker is asserted at `min(column edge, strip right − 104px)`, and the pointer-open test records the shell's focus hand-off explicitly.
- `openspec validate webclient-message-typesetting --strict` — valid. `tools.spec_traceability check` before sync: 1728/1728 covered; the two new annotations name the ADDED requirement IDs and resolve at the archive sync.
