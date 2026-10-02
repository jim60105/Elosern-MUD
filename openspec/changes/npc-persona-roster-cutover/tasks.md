Apply on branch `feat/npc-persona-roster-cutover` in worktree `.worktrees/npc-persona-roster-cutover`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. All fixtures are synthetic; no live model.

## 1. Design-document amendment

- [x] 1.1 Add a dated §13b amendment to `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` per design D2 (user-ordered supersession: pre-amendment databases are destroyed and re-initialized, not migrated; the §6.2 cutover mechanism is not implemented), add a superseded pointer at the top of §6.2 keeping its body as historical rationale, and correct the row-20 scope text in the §12.2 table.

## 2. Reset runbook

- [ ] 2.1 Write `docs/development/database-reset.md` per design D3: stop server, delete the SQLite database file named by the server settings (state the actual dev default read from `server/conf/settings.py`), `uv run --locked evennia migrate`, start and verify `startup_step`/roster-validation events; cover the retained test database `server/db/evennia-test.sqlite3` (or omitting `--keepdb` per AGENTS.md) and the container persistent DB volume; state the progress-destruction warning; link it from the development docs index if one exists.

## 3. Fresh-bootstrap and fail-closed tests

- [ ] 3.1 Add `world/rules/tests/test_npc_persona_fresh_bootstrap.py` (Evennia fixture per repo testing guide) pinning design D4 case 1: after the startup syncs run, every NPC-family instance carries the current content-generation marker and a contract-valid complete card, and `STARTUP_STEP_ORDER` contains the roster-validation step and no cutover step.
- [ ] 3.2 Pin design D4 case 2 in the same module: a hand-authored synthetic fixture in the pre-amendment occupant shape (old optional three-field `persona` plus `background`, shape copied via `git show` of the durable schema at the commit before `npc-persona-generated-quest-cards`) is rejected by the strict restore/codec path with a named validation failure; assert the quest is not restored.
- [ ] 3.3 Pin design D4 case 3: the runbook file exists and names the migrate command and the retained test database path (docs-contract test, same pattern as `tests/test_command_docs.py`).

## 4. Gates

- [ ] 4.1 Register `world.rules.tests.test_npc_persona_fresh_bootstrap` in exactly one rules shard of `.github/evennia-shards.json` and verify `tests.test_evennia_test_optimization_contract`; annotate the three new requirements with literal IDs from `uv run --locked python -m tools.spec_traceability list` and verify `tools.spec_traceability check`.
- [ ] 4.2 Run `uv run --locked python -m tools.contract_gate`, `tools.test_data_lint check`, `git diff --check`, and `openspec validate npc-persona-roster-cutover --strict`; confirm `tools.observability_freeze.json` and the observability catalog are untouched (no new events ship).
