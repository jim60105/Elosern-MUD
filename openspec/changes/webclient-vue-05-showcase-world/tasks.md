## 1. Build the world + services family (offline)

- [ ] 1.1 `LocalMap` as SFC + stories + tests (lattice states, actionable adjacent nodes, legend + detail line, colorblind-safe not-color-only)
- [ ] 1.2 `ArtPanel` as SFC + stories + tests (16:9 scene + portrait overlay; truthful placeholder when unavailable; label/alt outside the bitmap)
- [ ] 1.3 `ShopPanel`, `QuestBoard`, `LoreDrawer` as SFCs + stories + tests (from the mock `services` payload only)
- [ ] 1.4 `InventoryPanel` as SFC + story + tests (equipped items only; full bag deferred)

## 2. Manifest + gate

- [ ] 2.1 Extend the required-component manifest with the world + services keys and assert no full bag and no party panel are present
- [ ] 2.2 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [ ] 3.1 Add the `@covers_requirement`-annotated Python test (wrapping the Vitest/Storybook execution) for the new `webclient-component-showcase` map/art/services requirement, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
