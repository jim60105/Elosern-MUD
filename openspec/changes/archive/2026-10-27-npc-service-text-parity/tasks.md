# Tasks

## 1. Complete the bounded production cutover

- [x] 1.1 Add services <npc> with alias 服務 to the existing character cmdset and append the same projection to 看 <NPC>. Use existing visible target resolution and print none/unreadable/paused states distinctly without materializing state; include stable key and route guidance.

- [x] 1.2 Extend actual CmdShopStock (shop stock), CmdBuy/CmdSell (buy/sell), guild register/list/accept/turnin/ordinary-abandon and CmdGuildExam (guild exam) parsers with terminal @#<positive dbid>. Explicit input uses require_service_target without fallback; omission keeps implicit ambiguity behavior. Keep private escort abandonment, tracking and personal commands host-independent. Preserve all existing aliases; do not invent shop list or combat exam.

- [x] 1.3 Regress the church join <npc> explicit-target syntax and command-input-only handoff already completed by P; preserve enrollment/arousal/permission rules. Test that opening a command route sends nothing until the player submits, including stale target refusal with a second clergy present.

- [x] 1.4 Test text/web projection parity and execution with two providers, moved/hidden/off-anchor/paused targets and unchanged canonical state on discovery/rejection. Update both command references, curated manifest and relevant current delta traceability/ownership in this same slice.

## Handoff evidence

Every checkbox includes its named behavior tests and current documentation. Complete all implementation edits before the single focused verification batch in design.md. Report commands/results, changed spec coverage and preserved non-goal regressions. Proposed new focused labels must be implemented as permanent tests, not mocks or source-text checks. Do not run tests during this planning change.
