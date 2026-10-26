# Tasks

## 1. Complete the bounded production cutover

- [x] 1.1 Delete imported title property/required/check/write and remove title from every shipped reference card/example and helper. Test title-free NPC/player imports plus legacy-field rejection while literal stats, age/sex/kits/persona and name collisions stay strict.

- [x] 1.2 Delete authored host_title/title across place/shop/guild/adventurer/roster carriers and producers; remove NPC.npc_title and title validator/constants. Keep existing narrative identity prose and all name/profile/rank/schedule fields. Verify source-managed sync remains idempotent with H/D.

- [x] 1.3 Delete title end-to-end through generic/generated blueprint immutable carriers, canonical codecs, prompts/templates, characterization, compile and materialization. Exercise deterministic round trips and actual generated-package materialization with name/persona/age/portrait and no title.

- [x] 1.4 Update current delta specs and authoring guides docs/development/{adding-npcs,llm-scenarios}.md, docs/gm/characters.md, docs/game/npc-persona-editor.md and the active proposal amendments listed in section 11.4 of docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md. Keep historical files untouched; update behavior-based tests and traceability ownership.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
