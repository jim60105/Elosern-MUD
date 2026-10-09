## 1. Predecessor and Contract Context

- [x] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [x] 2.1 Implement the complete begin/read/release hold APIs and schedule-source consultation with persisted identity/timing and storage/cache snapshots; verify synthetic exam-owned movement/state deferral and unrelated-NPC ordering in world.rules.tests.test_guild_exam_schedule_hold.
- [x] 2.2 Implement ordered real-Exit replay and consumed-through persistence without nested clock advance; verify release/retry/crash snapshots and crossed weekly departure once in that focused module.
- [x] 2.3 Expose known/indeterminate hold reads and preserve startup source-registration ordering; verify corruption/silencing behavior in the focused module. Lifecycle owns later start/terminal/recovery wiring; planned-npc-service-windows owns reader integration, so this task edits neither successor.

## 3. Traceability, Documentation and Handoff

- [x] 3.1 Update affected owning game/development authoring documentation; obtain existing canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Map every new delta requirement/scenario to assertions for the authorized archiver, who synchronizes the delta and obtains/adds new canonical IDs after sync. Apply does not sync or archive. Verify no obsolete caller/contract remains.
- [x] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [x] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [x] 3.4 Run one final focused verification batch: Focused synthetic real-Exit weekly departure test across exam accumulated-time settlement, pass/fail/flee/invalid recovery and duplicate release; assert unchanged final world tick versus one combat settlement and unaffected other NPC ordering. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate guild-exam-schedule-hold --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.

## Apply evidence

The predecessor is archived at `2026-10-08-weekly-npc-schedule-cycles`, with all
tasks complete and live `ParsedSchedule.cycle_days`, `due_occurrences`, real Exit
settlement and clock surface registrations present.

Focused command:
`uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_exam_schedule_hold world.rules.tests.test_npc_schedule_runtime.StartupClockSourceOrderTests world.rules.tests.test_npc_schedule_runtime.WeeklySettlementTests`
passed 20 tests in 4.417 seconds. The initial run exposed five assertion errors
because day-boundary clock events do not carry `npc_id`; assertions now explicitly
select NPC schedule events. Main authorized continuation after that red signal.
A combined test/gate invocation was rejected by the test guard before execution;
the supported standalone command above supplied the passing evidence.

`uv run --locked python -m tools.contract_gate` passed traceability (2009
requirements, zero uncovered/errors), observability (zero violations), test-data
(zero violations), manifests and 18 contract tests.
`openspec validate guild-exam-schedule-hold --strict` passed.
No browser behavior changes; browser manifests and freeze lists remain unchanged.
No production exam starts/recovery wiring or main-spec synchronization performed.

Observed synthetic smoke for pass/fail/flee/invalid recovery API sequences:
before settlement the host stays home in exam state; combat advances once from
86395 to 86401, the other NPC traverses its real Exit and updates state at 86400.
After normal-state restoration, release traverses the host Exit once, sets busy,
persists consumed identity `(86400, 1)` and leaves world tick at 86401.
Duplicate release produces no events/traversal. Fault snapshots assert identical
durable hold, location/state, room contents caches and world tick after rollback.

### Archive traceability mapping

Obtain new canonical IDs only after authorized delta synchronization. Existing
runtime ID came from `uv run --locked python -m tools.spec_traceability list`
and its `--json-output /tmp/guild-exam-hold-ids.json` export.
All methods below are in `world.rules.tests.test_guild_exam_schedule_hold.ExamScheduleHoldTests`.

* Active exams defer host schedule occurrences and release through shared
  traversal: `test_weekly_departure_after_synthetic_terminal_sequences`
  establishes Weekly departure crossed and Other NPC; locked Exit, veto,
  silencing, same-tick assignment and effective-from methods assert authority
  boundaries. The terminal-sequence test already carries the existing runtime
  source requirement ID.
* Held interval release is recoverable and idempotent:
  `test_pending_and_completed_release_survive_cold_cache` establishes Crash/retry
  release; `test_marker_persistence_failure_restores_storage_location_and_caches`
  establishes Fault release. Outer-lifecycle and clock rollback tests assert the
  storage/cache snapshot contract; corruption/read and silencing methods assert
  indeterminate and unchanged startup contract boundaries.
* The modified runtime Held host scenario is asserted by the terminal-sequence
  test; unchanged runtime scenarios retain existing coverage, including the
  focused existing startup recovery and weekly settlement tests above.

## Rubber-duck disposition

The required blocking post-implementation review completed with no blocking
findings and two non-blocking findings.

* Impossible active consumed cursor: adopted. Reads now reject every non-null
  cursor on an active record, and the corruption behavior test includes an
  in-range bogus cursor. Validation of a released cursor against the current
  schedule is intentionally not adopted, because the authoritative schedule can
  be reassigned after release and would make a valid historical marker appear
  corrupt. The persisted marker remains a historical occurrence identity.
* Concurrent ownership/release: documented the serialized deterministic-game-loop
  caller contract, matching clock settlement. Concurrent worker/web-thread
  mutations are unsupported; lifecycle must route through the game loop.
  Row-lock machinery is not added to this SQLite, single-game-loop core.
  Production ingress enforcement remains owned by the lifecycle successor.

All review findings are resolved or explicitly dispositioned. The reviewer read
the finished worktree source/tests/specs/docs but could not inspect the exact Git
diff with its available tools; it did not rerun checks.

After the review fix, the same focused command passed all 20 tests in 4.329
seconds. The contract gate passed again, including both lints and all 18 contract
tests; strict change validation passed again.
