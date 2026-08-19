## 1. Phase-0 public contract audit

- [ ] 1.1 Enumerate every implementation-bound contract across `openspec/specs/webclient-*/spec.md` and the `web/tests/browser/` suite: the `window.Elosern.*` façades, the WebClient-plugin `onKeydown` path, `getElementById` / `#` target ids the keyboard router and Playwright assert, and the versioned layout-persistence keys
- [ ] 1.2 Classify each identified contract as preserve-via-bridge or delta, recording the affected requirement, the decision, the target change (C2), and the rationale
- [ ] 1.3 Freeze the façade-bridge surface (the exact `window.Elosern.{Protocol, KeyboardRouter, narrativeInput, actions.submit}` members) and the complete `MODIFIED`/`RENAMED` delta list; commit both as this change's `audit.md`
- [ ] 1.4 Confirm the frozen list is self-contained (C2 can apply it without re-deriving it) and that A1 modifies no source spec, server, transport, or `js/elosern` file

## 2. Commit the 設計稿 to docs

- [ ] 2.1 Copy the validated 設計稿 (`index.html` + its self-hosted font/asset files) into `docs/design/` as a self-contained offline file set with no CDN references
- [ ] 2.2 Add a `docs/_sidebar.md` design-draft entry linking the 設計稿
- [ ] 2.3 Add a dependency-free top-level test asserting the 設計稿 file exists under `docs/`, is linked from `docs/_sidebar.md`, and references no remote/CDN asset
- [ ] 2.4 Run the new top-level test and the docs check green; confirm this change touches no other capability, server, OOB, or transport file

## 3. Traceability (archive gate)

- [ ] 3.1 Add the `@covers_requirement`-annotated Python test for the new `webclient-browser-verification` frozen-contract requirement (asserting `audit.md` exists with the frozen façade surface + complete delta list and is declared C2's input), then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
