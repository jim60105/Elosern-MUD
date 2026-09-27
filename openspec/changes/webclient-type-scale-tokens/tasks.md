## 1. Implement the bounded surface

- [ ] 1.1 Declare shared type/numeral tokens and migrate existing literal sizes and obsolete token uses, excluding map geometry; verify no unresolved token references with a throwaway inventory.
- [ ] 1.2 Migrate non-code numerals and ordinary UI away from monospace while preserving keycaps/maps/input; inspect changing vitals and prices.
- [ ] 1.3 Remove existing incidental CSS/source-text assertions rather than re-pin them; add only browser regression checks for floor/clipping and aligned numeric columns.
- [ ] 1.4 Inspect representative dense HUD, drawer and creation stories at 1920x1080, 1440x900 and 1280x720; correct overflow with bounded layout, not unreadable shrinking.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-type-scale-tokens --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
