## 1. Build the reactive store over the preserved reducer

- [ ] 1.1 Create the Pinia store under `web/webclient-app/stores/` that wraps the A2 reducer `lib` wrapper as its core and publishes committed snapshots atomically (single writer)
- [ ] 1.2 Expose the view slices matching the A2 architecture-reference contract so B components can bind to them in C4

## 2. Store behavior + integration tests

- [ ] 2.1 Add store integration tests: atomic new-epoch snapshot adoption, active-epoch revision ordering, old-epoch/revision rejection, and panel replacement
- [ ] 2.2 Assert committed-only reads (no partially applied state observable) and that the store holds only allowlist / text-sourced data

## 3. Gate

- [ ] 3.1 Confirm the Vitest store suite is green, the dependency-free Node gate and all existing gates are unchanged, and no transport/OOB/server/`base.html`/template file was touched

## 4. Traceability (archive gate)

- [ ] 4.1 Add the `@covers_requirement`-annotated Python test (wrapping the store Vitest execution) for the new `webclient-vue-application` reactive-store requirement, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
