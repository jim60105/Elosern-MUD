## 1. Build the action-dock family (offline)

- [x] 1.1 `ActionDock`, `DockMenu`, `DockMenuItem` as SFCs + stories + tests (framed grid, guidance line, focused/disabled cells, `action-`/`target-` keys, `data-testid`)
- [x] 1.2 `OptionCard`/`ChoiceCardRow` as SFCs + stories + tests (exact server-authored card shape; activation emits the exact OOB action intent — the `ui_action` envelope's `action_id` + `payload`, per design D1 "emit intents only")
- [x] 1.3 `ChoicePointBlock` as SFC + story + tests (ready and generating states; movable)

## 2. Manifest + gate

- [x] 2.1 Extend the required-component manifest with the action-dock family keys and confirm the component-coverage gate stays green
- [x] 2.2 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [x] 3.1 Add the Python behavior test (wrapping the Vitest/Storybook/coverage execution) for the new `webclient-component-showcase` action-dock requirement alongside the implementation; the `@covers_requirement` annotation is applied **at this change's archive** — the requirement ID is new and enters the traceability index only when the delta syncs into `openspec/specs/` at archive (an annotation with an ID not yet in the main specs fails the static check, per `docs/development/spec-test-traceability.md` and the B1 precedent) — after which `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow must be green at this change's archive
