## 1. Build the full overlays (offline)

- [x] 1.1 `SettingsOverlay` as SFC + stories + tests (fonts, type scale, reduced-motion, text-to-HTML toggle, colorblind; emits `options.*`)
- [x] 1.2 `CreationOverlay` as SFC + stories + tests (presets/custom/concept wizard; adult gate on both age and apparent_age; activate; emits `creation.*`)
- [x] 1.3 `MapOverlay` and `HelpOverlay` as SFCs + stories + tests (backed/onboarding content)

## 2. Freeze + gate

- [x] 2.1 Assert the deferred surfaces (Party panel, intimate/adult collapsible, full inventory bag, event-log Toasts) are absent and not mocked
- [x] 2.2 Freeze the required-component manifest at the complete set; the component-coverage gate enforces it
- [x] 2.3 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage (frozen) green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [x] 3.1 Add the `@covers_requirement`-annotated Python test (wrapping the Vitest/Storybook execution) for the new `webclient-component-showcase` full-overlay + deferred-absent + frozen-manifest requirement, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
