## 1. Implement the bounded surface

- [ ] 1.1 Apply prose typography to rendered and measurement surfaces together; exercise punctuation, mixed scripts, long paragraphs and ASCII-map exceptions.
- [ ] 1.2 Reposition marker and name underline without changing reader gates; verify typing and auto-beat playback still suppress the marker.
- [ ] 1.3 Update dialogue opening highlight and visual ornaments; test disabled-first, all-disabled and pointer-to-keyboard transitions without unintended dispatch.
- [ ] 1.4 Observe actual browser paging at all three acceptance sizes, prose scales and reduced/off; retain a regression only for measurement/reading boundary behavior.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-message-typesetting --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
