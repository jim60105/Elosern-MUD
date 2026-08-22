## 1. Build the reactive store over the preserved reducer

- [x] 1.1 Create the Pinia store under `web/webclient-app/stores/` that wraps the A2 reducer `lib` wrapper as its core and publishes committed snapshots atomically (single writer)
- [x] 1.2 Expose the view slices matching the A2 architecture-reference contract so B components can bind to them in C4 (committed reducer state, the status/time and connection-status slices, the committed `context_actions` suggestions view + choice-point state via the imported choice-point/option-card logic, the imported local-map model, the keyboard-router focus slice on the preserved `action-`/`target-` dock keys, and the narrative slice with imported-markup-pipeline token views), plus the single dispatch entry (dispatch-only, one mutation in flight, test-driven sender seam)

## 2. Store behavior + integration tests

- [x] 2.1 Add store integration tests: atomic new-epoch snapshot adoption, active-epoch revision ordering, old-epoch/revision rejection, and panel replacement
- [x] 2.2 Assert committed-only reads (no partially applied state observable) and that the store holds only allowlist / text-sourced data

## 3. Gate

- [x] 3.1 Confirm the Vitest store suite is green, the dependency-free Node gate and all existing gates are unchanged, and no transport/OOB/server/`base.html`/template file was touched

## 4. Traceability (archive gate)

- [x] 4.1 Add the Python behavior test (wrapping the store Vitest execution) for the new `webclient-vue-application` reactive-store requirement alongside the implementation; the `@covers_requirement` annotation is applied **at this change's archive** — the requirement ID is new and enters the traceability index only when the delta syncs into `openspec/specs/` at this change's archive (an annotation with an ID not yet in the main specs fails the static check, per `docs/development/spec-test-traceability.md` and the B1/B2 precedent) — after which `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow must be green at this change's archive
