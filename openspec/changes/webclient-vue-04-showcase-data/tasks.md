## 1. Build the data family (offline)

- [ ] 1.1 `StatusPanel` as SFC + stories + tests (gauges, counters, static traits, wallet, conditions + derived modifiers; not color-only)
- [ ] 1.2 `CharacterPanel` as SFC + stories + tests (details, equipped items, disguise display-only vs true traits, guild rank/merit, persona)
- [ ] 1.3 `SkillBook` as SFC + stories + tests (active/passive tabs, categories, search, category>group>skill, cost/target/cast detail)

## 2. Manifest + gate

- [ ] 2.1 Extend the required-component manifest with the data-family keys and assert the intimate/adult block is absent (not mocked)
- [ ] 2.2 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [ ] 3.1 Add the `@covers_requirement`-annotated Python test (wrapping the Vitest/Storybook execution) for the new `webclient-component-showcase` status/character/skill requirement, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the gate is green at this change's archive
