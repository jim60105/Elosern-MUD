# Tasks

## 1. Complete the bounded production cutover

- [x] 1.1 Add host_key derived from unique host_profile_key to ServiceHostRow validation; replace first-component lookup with canonical npc_profile_key lookup and fail-closed duplicate/person-ownership checks. Test reorder/add/remove/service-id edit preserve one dbref and display-name edits never select hosts.

- [x] 1.2 Implement six-slot managed-set reconciliation and explicit authored-field allowlists in the deterministic assembly owner; remove obsolete managed slots and preserve unrelated components. Test zero-capability declarations, mixed bindings, repeated sync and unchanged stock/restock/sexual state.

- [x] 1.3 Remove reused-host relocation and title/component-ID residue heuristics. Keep whole-row retirement under content_source/service_host provenance and existing deletion hooks. Test moved host stays moved, untagged NPC survives and an explicitly retired tagged host follows existing lifecycle cleanup.

- [x] 1.4 Wrap complete source batch preflight/assembly in atomic rollback with handler-cache restoration. Fault after add/update/remove and second-row creation; assert attributes, objects, slots and game state match before. Update host sync/authoring docs, current affected specs and ownership annotations.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
