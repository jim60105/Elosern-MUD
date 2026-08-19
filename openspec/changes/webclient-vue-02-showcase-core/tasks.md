## 1. Establish the component-showcase foundation

- [ ] 1.1 Seed the required-component manifest (`web/webclient-app/`) with the core families (`AppShell`, `TopBar`/`Header`, `ConnectOverlay`, `NarrativeFeed`, `UnreadIndicator`, `CommandDrawer`) and confirm the A2 component-coverage script reads it
- [ ] 1.2 Wire the core family into `.storybook/` and Vitest so `npm run build-storybook` + the component-coverage check run green offline

## 2. Build the core component family (offline, no transport)

- [ ] 2.1 `AppShell`, `TopBar`/`Header`, `ConnectOverlay` as SFCs + stories + Vitest tests (active mode, live regions, connection dot; A2 design tokens)
- [ ] 2.2 `NarrativeFeed` rendered through the preserved `narrative_markup` pipeline (allowlist render + degrade-to-literal-text path) + story + test
- [ ] 2.3 `UnreadIndicator` (unread count + jump to latest, polite live region) and `CommandDrawer` (input, history, `/` open, send, `Escape` focus) + stories + tests
- [ ] 2.4 Add a stable, unique `data-testid` to every interactive surface and verify no story or build makes a non-local request

## 3. Gate

- [ ] 3.1 Confirm `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage are green, the dependency-free Node gate is still green, and the app renders offline with every required core surface usable at 1440x900 and 1280x720

## 4. Traceability (archive gate)

- [ ] 4.1 Add `@covers_requirement`-annotated Python tests (wrapping the Vitest/Storybook/browser execution) for each new `webclient-vue-application` and `webclient-component-showcase` requirement (the two new capabilities introduced here), then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
