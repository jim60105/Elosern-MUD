# Tasks

## 1. Complete the bounded production cutover

- [ ] 1.1 Add the exact immutable direct schema and core validation/assembly owner; validate unknown/duplicate types, per-type required/optional kwargs, forbidden runtime fields and per-component binding/room references. Keep issuer_key optional and narrative dialogue unbound. Add pure boundary tests.

- [ ] 1.2 Cut imports schema/validator/loader to independent components and validated plans, deleting blueprint caches/overrides and profession-tier/schedule defaults. Preserve literal stats, 0..10000 ages, safe keys, sex, kits, references and full-batch rollback; reject components for PlayerCharacter targets as before.

- [ ] 1.3 Convert all hosted/hostless PlaceDefinition producers and derived roster types, including clergy venue metadata, using the explicit conversion table. Make all room resolution complete and fail-closed within atomic interior+host preparation; retain H identity/reconciliation and independent lifecycle ownership.

- [ ] 1.4 Delete profession modules/rulebook, import assembly facade, registry inventories/reference edges and obsolete tests/docs/examples. Update docs/development/adding-npcs.md, docs/gm/characters.md and GM world-data docs; keep history and the approved source untouched.

- [ ] 1.5 Test mixed person/place components on one host, zero components, complete batch failure before persistence and injected assembly rollback including handler caches. Regress shipped merchant dialogue, clergy, issuer identity fallback and preserved stock/schedules; update all changed current specs/traceability and test ownership.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
