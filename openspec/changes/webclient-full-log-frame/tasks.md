## 1. Implement the bounded surface

- [ ] 1.1 Adopt the shared header/frame without nesting modal ownership; test close/restore from each log opener.
- [ ] 1.2 Style input echoes in place with prose/map exceptions; exercise retained multi-response logs for content order and selection.
- [ ] 1.3 Add end-position-aware return control; test arrival while scrolled up, activation and open-at-latest.
- [ ] 1.4 Inspect log at three desktop sizes with long prose and wide map lines; verify no text is obscured by controls.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-full-log-frame --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
