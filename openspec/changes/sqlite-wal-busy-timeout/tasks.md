# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive (see Workflow follow-up).
Do not edit `compose.yaml`, `Containerfile`, `docker-entrypoint.sh`, `scripts/serve.sh` or any file under `world/`.

## 1. Connection options

- [ ] 1.1 Create `server/conf/sqlite_options.py` and edit `server/conf/settings.py` and `server/conf/test_settings.py` exactly as design D1 and D2 state. Verify: `uv run --locked python -c "from server.conf.sqlite_options import SQLITE_OPTIONS, SQLITE_TEST_OPTIONS; assert 'init_command' in SQLITE_OPTIONS and 'init_command' not in SQLITE_TEST_OPTIONS"` exits 0.
- [ ] 1.2 Add `server/conf/tests/test_sqlite_options.py` per design D4 and register it in `.github/evennia-shards.json`. Verify: the test prefix with `server.conf.tests.test_sqlite_options` passes, and the test prefix with `tests.test_evennia_test_optimization_contract` passes.
- [ ] 1.3 Verify the existing settings tests still pass: the test prefix with `server.conf.tests.test_env_overrides` passes.

## 2. World saves

- [ ] 2.1 Apply design D3 to `server/saves/snapshot.py` and add the snapshot test of design D4. Verify: the test prefix with `server.saves.tests.test_snapshot` passes.
- [ ] 2.2 Add the two restore tests of design D4 to `server/saves/tests/test_restore_tool.py`. Verify: the test prefix with `server.saves.tests.test_restore_tool` passes. If a new test fails against the unchanged `server/saves/restore.py`, stop and report the failure; do not redesign the tool.

## 3. Documentation and gates

- [ ] 3.1 Apply design D5. Verify: `grep -c sqlite_options docs/development/settings-and-environment.md` prints at least 1.
- [ ] 3.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.contract_gate --change sqlite-wal-busy-timeout` and `openspec validate sqlite-wal-busy-timeout --strict`. Verify: all exit 0.
- [ ] 3.3 Manual check, recorded in the hand-off as information only: start the server once with `scripts/serve.sh`, confirm `server/db/evennia.db3-wal` exists, stop the server.

## Workflow follow-up

- During archive, after the delta sync, annotate the new tests with the identifiers printed by `uv run --locked python -m tools.spec_traceability list` for the `sqlite-concurrency` requirement and the two new `gm-save-management` requirements.
