## 1. Implement the bounded surface

- [x] 1.1 Introduce the single resize-owned scale and derived dimensional/type/radius tokens; test clamp boundaries and teardown without pinning CSS text.
- [x] 1.2 Migrate fixed chrome dimensions once across the named surfaces, retaining existing vh-based band/prose/art formulas; inspect token and runtime dimension consumers for double multiplication.
- [x] 1.3 Scale minimap outward dimensions without changing SVG units; reconcile the fixed-square main contract at reference sizes and verify full-map fit/zoom.
- [x] 1.4 Measure actual 1080p/1440p reference pairs and observe three smaller acceptance sizes, long localized labels and maximum prose scale; test keyboard/pointer hit targets and browser zoom separately.
- [x] 1.5 Remove superseded ordinary radius literals and document geometry exceptions, without an exact-token/source-text guard.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-proportional-ui-scale --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
