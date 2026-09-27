## 1. Implement the bounded surface

- [ ] 1.1 Theme the existing native toggles and align settings cards/type without changing preference APIs; exercise keyboard checked-state changes.
- [ ] 1.2 Add isolated sample/replay with existing speed logic and timer cleanup; test no live-log/dispatch mutation and close mid-type.
- [ ] 1.3 Inspect scale/speed combinations and full/reduced/off in the actual settings overlay at three desktop sizes.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-settings-reading-preview --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
