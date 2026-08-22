## 1. Build the data family (offline)

- [x] 1.1 `StatusPanel` as SFC + stories + tests (gauges, counters, static traits, wallet, conditions + derived modifiers; not color-only)
- [x] 1.2 `CharacterPanel` as SFC + stories + tests (details, equipped items, disguise display-only vs true traits, guild rank/merit, persona)
- [x] 1.3 `SkillBook` as SFC + stories + tests (active/passive tabs, categories, search, category>group>skill, cost/target/cast detail)

## 2. Manifest + gate

- [x] 2.1 Extend the required-component manifest with the data-family keys and assert the intimate/adult block is absent (not mocked)
- [x] 2.2 Gate: `npm ci && npm run build && npm test && npm run build-storybook` + component-coverage green, the Node gate still green, and no story makes a non-local request

## 3. Traceability (archive gate)

- [x] 3.1 Add the Python evidence test (wrapping the Vitest/Storybook execution) for the new `webclient-component-showcase` status/character/skill requirement — landed now with its requirement mapping in the module docstring; the `@covers_requirement` annotation itself is applied at this change's archive with the delta sync (the B1/B2 precedent, since the requirement ID enters the traceability index only then). `uv run --locked python -m tools.spec_traceability check` is green now; the `verify --evidence` flow runs at this change's archive so the gate is green there
