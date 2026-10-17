# Tasks

## 1. Normal release presence and behavior regressions

- [x] 1.1 Extend `world/rules/tests/test_possession_transition.py` with synthetic real-session regressions for the actual `CmdUnpossess` 歸位 path and `release_for_party_change`, asserting shared-room live location, persisted `db_location_id`, room contents, retained membership at the release boundary, cleared bindings, and correct puppet/locks/cmdset. Verify these new room assertions fail against the unmodified release code; reuse the supplied reproduction rather than reconstructing the diagnosis.
- [x] 1.2 Implement occupied-room snapshot/restore in `world/rules/possession.py::_unpuppet` for the shared `handback` / `party_change` ladder. Restore after each unpuppet attempt, including a stash-then-raise hook, before owner re-puppet and synchronization; remove the companion's `prelogout_location` and any present `prelog_location`. Verify task 1.1 passes, the residual Attributes are absent, and an ordering assertion sees the companion in-room during handback synchronization. Preserve the existing binding-clear ordering in `release_possession`; do not add a typeclass override or alter the disconnect branch.
- [x] 1.3 In that same test module, prove both normal release reasons permit repeat `possess` with retained membership, then ordinary movement/following into a synthetic second room and inclusion by `combat_companions` under existing eligibility gates. Add a remote-companion case that keeps each body in its own pre-release room and a membership-removal continuation that removes the legitimate source while leaving the companion on-grid. Verify the tests exercise the real party helpers and assert identity, without relaxing gates or making terminal removal retain membership.
- [x] 1.4 Extend the existing entranced-body and sequence tests to assert the owner remains in room contents as 呆立入神 during possession, the marker clears after return, and the established retire/reset/synchronize sequence is unchanged. Verify these tests together with the new normal-release cases using the focused command in section 4.

## 2. Failure compensation and boundary observability

- [x] 2.1 Extend `world/rules/possession.py::snapshot_party_control` and `restore_party_control` with the companion's location and logout Attribute presence/value snapshots. Restore location before recovery puppeting and restore exact metadata after its hooks. Extend existing refused-return/write-failure tests and add a later outer party-control rollback case; verify durable and live locations, logout metadata, bindings, locks, cmdset and puppet return to baseline, and a successful retry removes residuals. Inject a failure after the new metadata cleanup so the test exercises the new rollback surface.
- [x] 2.2 Retain the existing `world.rules.possession.log_info` `possession_release` event in `release_possession` and its `char`, `npc`, `reason` keys; add the final companion `room` id, with no second restoration event. Document this boundary in §4.2 of `docs/superpowers/specs/2026-09-02-observability-logging-design.md`. Verify caller-binding log assertions for both reasons, no successful-release event on failure, and no duplicate event/movement/membership write for a repeated release; run observability lint in the focused batch in section 4.

## 3. Traceability and ownership

- [x] 3.1 Associate the real behavior methods with the existing release-ladder requirement using its canonical ID from `uv run --locked python -m tools.spec_traceability list`. For the ADDED room-preservation requirement, prepare an equivalent temporary repository tree containing the merged main spec and the corresponding tests, obtain its ID with `uv run --locked python -m tools.spec_traceability --repo-root=<equivalent-tree> list`, and apply that literal `covers_requirement` annotation to those behavior methods in the equivalent tree. Verify the equivalent tree's `check` passes and record the literal annotation and method mapping in the handoff. Do not add an unknown future ID to the live test tree before the main spec is synced, or claim the current-root gate covers the active delta. The sync-time activation is stated below.
- [x] 3.2 Keep all new tests in the existing registered `world.rules.tests.test_possession_transition` module; confirm it retains exactly one owner in `.github/evennia-shards.json` with `tests.test_evennia_test_optimization_contract`. No manifest edit is expected. If any test module is added, renamed, or moved during implementation, register it in exactly one shard in the same change and re-run that ownership contract. Verify no command surface changed; if it did, update both `docs/game/commands.md` and `docs/game/command-reference.md` and run `tests.test_command_docs` in the same change.

## 4. Focused integration verification

- [x] 4.1 Run the focused transition/core tests and observability lint below after all implementation changes land, and record their outputs. Verify all normal-release, retry, compensation, entranced-body, and existing disconnect-control tests pass without asserting disconnect spatial safety. Do not run the full suite or CI shard commands.
- [x] 4.2 Run the current-root traceability check, contract gate, and strict change validation below; record results and any independently existing blocker without weakening checks. Recheck the merged equivalent-tree traceability gate from task 3.1 so the new requirement has substantive coverage before archive.

Use an existing environment file containing `MUD_TEST_SETTINGS=1`, or a scratch file outside the tracked tree, substituted for `<test-env-file>`. The single-token `--env-file=<path>` spelling is required. Run these commands from the repository root, sequentially to avoid shared test database/pidfile contention.

```text
uv run --locked --env-file=<test-env-file> evennia test --settings test_settings.py --keepdb world.rules.tests.test_possession_transition world.rules.tests.test_possession
uv run --locked python -m tools.observability_lint check
uv run --locked --env-file=<test-env-file> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.contract_gate
openspec validate fix-possessed-companion-room-location --strict
```

For task 3.1's equivalent tree, use the existing tool's root override with the merged specs and the annotated test sources present.

```text
uv run --locked python -m tools.spec_traceability --repo-root=<equivalent-tree> list
uv run --locked python -m tools.spec_traceability --repo-root=<equivalent-tree> check
```

## Workflow follow-up

- At authorized spec synchronization/archive, activate the recorded literal `covers_requirement` annotation in the real behavior tests in the same change that makes the new main-spec requirement visible. Run `uv run --locked python -m tools.spec_traceability list`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked python -m tools.contract_gate` on that synced tree before handoff. A pre-sync pass alone is insufficient. Archive and sync are not part of this planning assignment.
- `fix-disconnected-possession-room-lifecycle` is the named separate follow-up for last-session unpuppet and independent link-dead maintenance room survival, as justified by the checked Evennia ordering in `design.md` §4. Do not silently claim it is implemented by these tasks.
