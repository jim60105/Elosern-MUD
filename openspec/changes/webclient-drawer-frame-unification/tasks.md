## 1. Implement the bounded surface

- [ ] 1.1 Introduce and migrate the presentational header in both hosts and gallery, preserving each existing modal lifecycle; test nested close/restore behavior.
- [ ] 1.2 Apply opaque panel and scrim treatment with no-filter fallback; inspect populated stage text behind settings and lineage.
- [ ] 1.3 Unify icon mapping with navigation and remove duplicate gallery header/close; verify visible labels and accessible names.
- [ ] 1.4 Update showcase manifest/spec and header story for the new component; inspect drawer bounds at all three desktop acceptance sizes with command line expanded.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-drawer-frame-unification --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
