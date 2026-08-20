## 1. Establish the component-showcase foundation

- [x] 1.1 Seed the required-component manifest (`web/webclient-app/`) with the core families (`AppShell`, `TopBar`/`Header`, `ConnectOverlay`, `NarrativeFeed`, `UnreadIndicator`, `CommandDrawer`) and confirm the A2 component-coverage script reads it
- [x] 1.2 Wire the core family into `.storybook/` and Vitest so `npm run build-storybook` + the component-coverage check run green offline

## 2. Build the core component family (offline, no transport)

- [x] 2.1 `AppShell`, `TopBar`/`Header`, `ConnectOverlay` as SFCs + stories + Vitest tests (active mode, live regions, connection dot; A2 design tokens)
- [x] 2.2 `NarrativeFeed` rendered through the preserved `narrative_markup` pipeline (allowlist render + degrade-to-literal-text path) + story + test
- [x] 2.3 `UnreadIndicator` (unread count + jump to latest, polite live region) and `CommandDrawer` (input, history, `/` open, send, `Escape` focus) + stories + tests
- [x] 2.4 Add a stable, unique `data-testid` to every interactive surface and verify no story or build makes a non-local request

## 3. Gate

- [x] 3.1 Confirm `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage are green, the dependency-free Node gate is still green, and the app renders offline with every required core surface usable at 1440x900 and 1280x720

## 4. Traceability (archive gate)

- [ ] 4.1 Add the Python behavior tests (wrapping the Vitest/Storybook/`dist`/component-coverage execution) for each new `webclient-vue-application` and `webclient-component-showcase` requirement (the two new capabilities introduced here) alongside the implementation; then apply the `@covers_requirement` annotations **at this change's archive** — the requirement IDs are new and enter the traceability index only when the deltas sync into `openspec/specs/` at archive (per `docs/development/spec-test-traceability.md`: the owning change carries the behavior test so the annotation can be added when the main identifier exists; an annotation with an unknown ID fails static `check`) — then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive (at apply: static `check` green with no unknown IDs, all three entry points green in-session; at archive: annotation added with the sync, then the full `OPENSPEC_TEST_EVIDENCE` + `verify --evidence` run)
