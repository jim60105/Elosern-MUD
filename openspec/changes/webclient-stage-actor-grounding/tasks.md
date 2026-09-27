## 1. Implement the bounded surface

- [ ] 1.1 Add the stage-only artwork variant, contour-preserving shadow and silhouette states; inspect done, missing, pending and load-failed stories with both alpha and opaque inputs.
- [ ] 1.2 Keep drawer captions unchanged and preserve speaking/beat transitions; verify actor identity and state through accessible component assertions.
- [ ] 1.3 Exercise 1280x720, 1440x900, 1920x1080 geometry with vitals, expanded command line and one to three foes; observe non-occluded labels and no new scroll.
- [ ] 1.4 Exercise full/reduced/off on the actual stage; retain behavior regression for missing versus pending and motion preference transitions.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-stage-actor-grounding --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
