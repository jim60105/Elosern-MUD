# Tasks

Apply worker **gpt-luna** must use branch `feat/fix-body-sleep-lifecycle` and worktree `.worktrees/fix-body-sleep-lifecycle`. This checklist is implementation work, not authorization to apply during proposal creation. Each group lands its behavior tests/docs together; main worker runs focused checks once after all edits. Preserve unrelated map proposal and never edit live saves.

## 1. Accepted per-body sleep contract

- [x] 1.1 Add validated durable sleep receipt/target lifecycle at the existing time-skip owner, including forced transition receipt creation, bounded replay identity/results, stable locks/revisions and no replacement of active plans. Verify synthetic reload, stale/concurrent retry and missing/corrupt-state tests demonstrate no replay/refill/wake repair.
- [x] 1.2 Implement duration and until-recovered targets with existing parser/skip caps, full HP/MP/SP plus mental target and zero-duration reconciliation. Add independent examples proving 180000 reserve needs 15000 seconds, slowest gauge governs recovery, full reserve does not shorten `sleep 2h`, and capped recovery reports partial recovery.
- [x] 1.3 Amend approved fatigue/sleep design header/§16 and §4.2/§9.1 receipt/target semantics as specified in design.md; verify archived original work and proposed corrections are distinguished, with no migration or compatibility path.

## 2. All-body settlement and explicit party selection

- [x] 2.1 Integrate voluntary receipt boundaries into mental-time/clock settlement and reconcile every applicable sleeping body, without changing possession. Extend time-skip/clock/possession tests to possess a companion for real, recover the owner through that companion's wait or sleep, reload, and prove owner AWAKE while companion control remains selected.
- [x] 2.2 Preserve indivisible full action effects and terminal-only combat while accounting for a pre-existing voluntary wake deadline and awake remainder; add mixed activity/resource/practice tests proving sleeping bookings remain and no sleeping interval earns practice or recovery twice.
- [x] 2.3 Add the explicit all-present-effective-party entry operation with complete preflight and one atomic multi-body posture/receipt commit. Verify mixed awake/voluntary/forced targets, remote members unchanged, repeated identity, one ineligible member refusal and SKIP without party selection.
- [x] 2.4 Register receipt, target/cursor, replay result and projection caches in the existing entry/advance compensation. Fault after posture, second member, clock, resource and wake writes; verify persisted/reloaded and in-process state, bookings, tick and events restore together.
- [x] 2.5 Update fatigue/sleep design §8.4/§8.5/§11/§12 and receipt consumer contract alongside these rules tests, documenting only the pre-existing voluntary-deadline exception inside indivisible actions; verify full atomic action effects and completion-time collapse remain, and passive wake neither repuppets owner nor widens unrelated resource scope.

## 3. Thin command and action consumers

- [x] 3.1 Wire `sleep [<duration>|until-recovered]`, `sleep all [<duration>|until-recovered]`, `sleep continue` and alias through shared operations; amend the original explore.wait requirement and strict payload validation to the documented scope/mode/seconds contract. Verify real command and adapter tests accept plain recovery, explicit party recovery and duration sleep, distinguish ordinary duration wait, reject every malformed combination in the delta, forbid target reset and publish no fictitious completed-sleep result.
- [x] 3.2 Update `docs/game/commands.md`, `docs/game/command-reference.md` and command-doc contracts for duration/recovery/party/continue syntax and sleeping-view availability. Keep dream-before-recovery consumer cutover in the dependent change; verify documentation accurately distinguishes this API and current dream surface.
- [x] 3.3 Add/move tests only with exact `.github/evennia-shards.json` ownership and annotate changed/new main requirements using canonical IDs from `uv run --locked python -m tools.spec_traceability list`; verify no production-data echo tests or unmapped new modules.

## 4. Focused integration evidence

- [x] 4.1 Main apply worker runs the smallest changed clock/fatigue/time-skip/possession and real command labels with `uv run --locked --env-file=<test-env> evennia test --settings test_settings.py --keepdb <labels>`; record results for passive owner wake, exact duration, atomic multi-body failure and reload. Do not rerun the reported original smoke failure.
- [x] 4.2 Run `tests.test_command_docs`, relevant shard/frozen ownership contracts, `uv run --locked python -m tools.spec_traceability check`, observability lint if logging changes, and `uv run --locked python -m tools.contract_gate`; verify receipt events occur only after commit with stable IDs and no repeated success on retry.
- [x] 4.3 Run `openspec validate fix-body-sleep-lifecycle --strict` and record focused evidence plus remaining CI-owned coverage. No full CI shard, full browser suite or complete `verify --evidence` run locally.
