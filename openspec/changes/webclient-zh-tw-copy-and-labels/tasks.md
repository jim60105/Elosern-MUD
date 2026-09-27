## 1. Implement the bounded surface

- [ ] 1.1 Translate help and client enum/party copy from actual bindings; verify identifiers and action payloads do not change.
- [ ] 1.2 Localize condition helper and readable chip names; test modifiers with signs/units, unknown keys, duration and overflow.
- [ ] 1.3 Resolve codex race display titles from registry in the existing read-model path; test registry-backed title with stable opaque keys.
- [ ] 1.4 Remove redundant server-generated timestamp labels and render structured relative/exact local dates; test fixed clock/time zone, future and out-of-calendar timestamps plus timer teardown.
- [ ] 1.5 Inspect help, conditions, skill target descriptions, codex, party and gallery on the real client; no tests asserting translation dictionaries merely echo themselves.

## 2. Verify and document the completed behavior

- [ ] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [ ] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [ ] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [ ] 2.4 Run `openspec validate webclient-zh-tw-copy-and-labels --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.
