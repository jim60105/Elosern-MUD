# Tasks

## 1. Complete the bounded production cutover

- [ ] 1.1 Cut over GuildExamReception/guild_exam_reception in component declaration, vocabulary, rulebook, all counter readers, commands/presenters and fixtures; remove every old class/slot/type alias. Assert attach/save/reload and counter discovery use only the new slot.

- [ ] 1.2 Delete GuildAdventurer.profession and db.profession writes/validation, preserving person provenance, qualification registry and initialization. Test qualified adventurers retain their dbrefs, kit, schedule and no reception component after repeated sync.

- [ ] 1.3 Exercise reception request -> exact qualified adventurer through schedule-only and actual-start cases; regress insufficient merit, wrong branch, active exam, rollback and current recruitability. Update current counter documentation and affected delta traceability without changing examination mechanics.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
