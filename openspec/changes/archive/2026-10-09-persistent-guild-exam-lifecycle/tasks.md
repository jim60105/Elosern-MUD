## 1. Predecessor and Contract Context

- [x] 1.1 Read the live source and completed predecessor deltas listed in proposal.md; verify required APIs/data exist and use the same registry/service/skill/schedule/snapshot patterns. No stub or compatibility fallback is acceptable.

## 2. Owned Implementation and Behavior

- [x] 2.0 Wire the predecessor begin/read/release hold APIs atomically into start and every terminal/recovery path; verify active host movement/state deferral and crossed departure once in world.rules.tests.test_guild_exams and world.rules.tests.test_guild_exam_schedule_hold, without double time.

- [x] 2.1 Preflight and select qualified persistent host; cut rank-owned identity fields/factory/deletion contracts and migrate every consumer/fixture/inventory reference. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.2 Implement atomic snapshots, real kit/restriction activation, session publication and affinity rollback including ORM/handler mirrors. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.3 Implement terminal normal restoration, idempotent rank/title settlement and coherent/invalid cold-start recovery without host deletion. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.
- [x] 2.4 Exercise all terminal outcomes, repeated E-B same-host identity, collision discipline and fault injection at every persistence/cache boundary. Verify with the matching scenarios in specs/ and focused checks described in design.md, collected in the final batch after all owned edits land.

## 3. Traceability, Documentation and Handoff

- [x] 3.1 Update affected owning game/development authoring documentation and synchronize this delta via the repository OpenSpec workflow during authorized archive; obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list` and annotate only substantive discoverable behavior tests. Verify every delta requirement/scenario has matching assertions and no obsolete caller/contract remains.
- [x] 3.2 Register each new/moved non-browser module and new browser method exactly once in `.github/evennia-shards.json` / `.github/browser-shards.json`; separate tagged authored-data checks under existing freeze discipline. Verify exact ownership and no freeze-list expansion or data-echo mechanics assertions.
- [x] 3.3 Update the approved parent design references where this slice supersedes earlier mechanics, preserving numeric/evidence qualifications; verify implemented documentation matches authored/runtime shapes.
- [x] 3.4 Run one final focused verification batch: Focused guild exam and combat-session recovery tests plus title rollback tests; actual persistent host/pair/accessory smoke over two attempts, base/skill/proficiency/persona/dbref unchanged, full normal pools restored. Synthetic corruption/fault cases assert byte-equivalent snapshots and retry exactly once. For Evennia use `uv run --locked --env-file=<existing-test-env> evennia test --settings test_settings.py --keepdb <focused-label>` with the repository test guard; browser uses one bounded `web.tests.browser.unittest_driver` method/class. Run `uv run --locked python -m tools.contract_gate`, affected observability/data lints and `openspec validate persistent-guild-exam-lifecycle --strict`; record exact commands/results and smoke snapshots. No full browser suite or complete evidence verification locally.
