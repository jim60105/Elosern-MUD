# Tasks

## 1. Complete the bounded production cutover

- [ ] 1.1 Remove NPC composition helpers/full_identity flags and migrate every named runtime consumer to its existing plain-name boundary, including dialogue budget preview, room appearance, party targeting and prompt context. Add sentinel/raising-accessor behavioral cases and plain-key ambiguity regression.

- [ ] 1.2 Remove npc_title from private editor API, exact Python/UMD validators, editor header/view, stories and intercept fixtures in one cutover; verify read/update versions, dirty draft and offline greeting semantics remain unchanged.

- [ ] 1.3 Remove title and duplicate profession summary rows from GM NPC list/detail without removing technical components. Test game/text/GM labels agree and neither frontend imports components from the other app.

- [ ] 1.4 Update current display/editor specs, docs/game/npc-persona-editor.md and authoring presentation guidance; retain title-authoring instructions only until N removes their producer contract. Regress player title behavior and unchanged party/possession eligibility; update shard/traceability ownership.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
