## 1. Implement the bounded surface

- [x] 1.1 Compact participant rows, names, thumbnail states and HP hairlines; verify six participants and long names remain readable.
- [x] 1.2 Add foe names and non-colour acting/target cues from existing presentation state; test no target activation is introduced and HP stays synchronized.
- [x] 1.3 Replace the combat ribbon and zero-round wording only; verify canonical positive counts are unchanged.
- [x] 1.4 Run a stage journey at the three acceptance sizes with three foes, six participants and terminal playback; observe head clearance and no stage scroll.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-combat-participant-polish --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
