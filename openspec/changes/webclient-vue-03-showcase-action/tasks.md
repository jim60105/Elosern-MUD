## 1. Build the action-dock family (offline)

- [ ] 1.1 `ActionDock`, `DockMenu`, `DockMenuItem` as SFCs + stories + tests (framed grid, guidance line, focused/disabled cells, `action-`/`target-` keys, `data-testid`)
- [ ] 1.2 `OptionCard`/`ChoiceCardRow` as SFCs + stories + tests (exact server-authored card shape; activation emits the OOB envelope)
- [ ] 1.3 `ChoicePointBlock` as SFC + story + tests (ready and generating states; movable)

## 2. Manifest + gate

- [ ] 2.1 Extend the required-component manifest with the action-dock family keys and confirm the component-coverage gate stays green
- [ ] 2.2 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [ ] 3.1 Add the `@covers_requirement`-annotated Python test (wrapping the Vitest/Storybook execution) for the new `webclient-component-showcase` action-dock requirement, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
