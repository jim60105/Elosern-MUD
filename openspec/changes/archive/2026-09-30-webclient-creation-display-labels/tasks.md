## 1. Implement the bounded surface

- [x] 1.1 Extend the registry-derived race read model and exact panel to v6; test label bounds, preset references and unknown-field rejection in both validators.
- [x] 1.2 Migrate registration, fixtures and all protocol consumers to v6 in one cutover; verify v5 is rejected rather than silently adapted.
- [x] 1.3 Render supplied race labels in all creation views while retaining opaque submission keys; exercise preset and custom confirmation.
- [x] 1.4 Disambiguate server-owned axis vocabulary and preview consumers; test changing one axis leaves the other unchanged and total budget enforcement remains intact.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-creation-display-labels --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
