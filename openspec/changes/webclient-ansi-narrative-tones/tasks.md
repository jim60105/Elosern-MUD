## 1. Implement the bounded surface

- [ ] 1.1 Apply the authored chromatic table and cube saturation cap in the generator, using the band contrast reference and unchanged background entries; regenerate the stylesheet.
- [ ] 1.2 Retain deterministic palette drift/class coverage and add numerical contrast/saturation/hue boundary checks; do not assert every authored table literal as a behavior test.
- [ ] 1.3 Load the generated palette in Storybook and inspect muted ANSI and grayscale prose on the actual message band and full log; record rendered contrast checks for normal-sized text.
- [ ] 1.4 Preserve reduced/off blink behavior and ASCII-map alignment through the existing renderer; run the focused palette test and browser smoke.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-ansi-narrative-tones --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
