## 1. Implement the bounded surface

- [x] 1.1 Introduce a stable fixed-width primary region (packed against its trailing edge; see design.md) and preserve mode absence; inspect exploration/combat and unavailable gallery at three acceptance widths.
- [x] 1.2 Share the tool model (`nav-tools.js`, glyph keys and labels) with header consumers and add the shared hover/Tab-focus tooltip; test Escape dismissal, the second Escape, the quiet restored opener, and unchanged activation. Update the tests that asserted the retired native `title` (`desktop_navigation.test.js`, `test_browser_contextual_hud_stage.py` tool-group journey).
- [x] 1.3 Polish brand baseline and place-card hierarchy using type/numeral tokens; inspect long place names and complete world time.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-chrome-navigation-polish --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
