## 1. Predecessor and Contract Context

- [x] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [x] 2.1 Implement presence-first coordinator with immutable schedule outcome and authoritative start delegation; route command/intent through it. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.2 Cut services producers/validators/action registry/client/stories/fixtures to v5 and exact new fields/action; keep enabledness independent of merit/presence. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.3 Update messages/calendar formatting, command docs and master/schedule-design amendments; remove obsolete aliases and local-generic-host assumptions. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.4 Add focused adapter/command/intent parity and keyboard browser method proving below-merit absent schedule then present merit rejection, plus eligible start. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [x] 3.1 Update affected owning game/development authoring documentation and synchronize this delta via the repository OpenSpec workflow during authorized archive; obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains.
- [x] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [x] 3.3 Update `docs/game/commands.md` and `docs/game/command-reference.md`, master engine §5.4/§7.4 and NPC schedule design §3.1/§8; verify the command-doc contract and absence of all old action/field aliases.
- [x] 3.4 Run one final focused verification batch: Focused service-view/messages/action/command/intent and Python/Node/component tests; one bounded browser method/class at existing acceptance viewports 1451x790 and 2560x1440, registered exact shard ownership. Observe real host weekly traversal, enabled below-merit action, exam_schedule with byte-equal state, present BELOW_THRESHOLD then eligible exam_started. No full managed browser suite. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate guild-exam-appointment-surface --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

## Implementation Notes

- Coordinator: `world/rules/guild_exam_request.py::request_guild_exam` (singular module name: `tests/test_guild_economy_guards` forbids the substring `requests` in `commands/combat.py`); target resolution `world/rules/guild_exams.py::resolve_exam_request_target`; new reasons `examiner_busy`, `schedule_blocked`, `attendance_unknown`, `top_rank`.
- 3.1: the delta was synced at archive; `guild-exam-requests::*` annotations were added then to the coordinator, adapter, validator and intent behavior tests (traceability check: 2028 covered, 0 uncovered). Synced main requirement statements keep the concise form required by strict validation, with detail carried by the delta scenarios.
- Browser harness: the synthetic boot stops at shipped roster validation before `sync_npc_schedules`, so `install_synth_services_catalog` now registers the NPC-schedule clock source alongside the caravan/shop sources it already re-registers.
- Final focused batch: Evennia focused labels (coordinator, exams, service view, intents, commands, service actions/validators/registry, presenter, parity, command docs, shard and frozen contracts), Node gate 519/519, vitest 13 files 209/209, `GuildExamAppointmentJourney` at 1451x790 and 2560x1440, `tools.contract_gate` passed, `openspec validate guild-exam-appointment-surface --strict` passed.

