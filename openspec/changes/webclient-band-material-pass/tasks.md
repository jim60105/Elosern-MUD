## 1. Implement the bounded surface

- [ ] 1.1 Apply seam, divider and shared control-strip geometry; inspect exploration/dialogue/combat with captions and expanded command line.
- [ ] 1.2 Make popover opaque and remove only its duplicate heading; exercise back/escape and disabled actions without dispatch leakage.
- [ ] 1.3 Simplify container/command-line focus and style the existing secondary footer buttons; walk keyboard focus on the live client.
- [ ] 1.4 Replace the panel flip with motion-token variants; inspect full/reduced/off without pinning CSS source.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-band-material-pass --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
