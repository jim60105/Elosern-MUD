# Tasks

Worker: luna
Branch: `feat/settle-terminal-combat-fatigue`
Worktree: `.worktrees/settle-terminal-combat-fatigue`

## 1. Terminal settlement and opening defeat

- [ ] 1.1 Extend `world/rules/combat_session/settlement.py::settle_session` to derive recorded posture intervals and settle mental time once with the existing marker. Extend combat-flow/persistence tests for ten rounds (60 seconds), awake 0.1%-to-zero collapse, threshold sleeper wake and a synthetic four-sleep/six-awake interval; verify unchanged live reserve and no retrospective recovery.
- [ ] 1.2 Add the canonical all-forced-sleep opening condition after target/participant validation and before first command/round. Use existing zero-round terminal defeat/exam_failed writer; extend direct valid engagement tests for ordinary aftermath, exam policy, invalid target rejection and repeated terminal/reload idempotency without spectator mode.
- [ ] 1.3 Preserve defeated/dead state and existing non-fled terminal scope; schedule handoff only after complete aftermath commit with actual eligible survivors. Extend flow/defeat tests for no physiological revival, candidate removed by the same terminal unit and below-threshold stationary victory; document these consequences in both existing command pages.

- [ ] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. Complete rollback and runtime boundary evidence

- [ ] 2.1 Extend `world/rules/combat_session/snapshot.py::_snapshot_round_touched`, `_snapshot_round_clock` and fatigue-surface declarations to cover all member reserve/posture/buffs, activity/session/draft metadata, clock and later aftermath surfaces. Inject faults after projection and after later terminal writes; verify durable reload and in-process caches both restore before retry.
- [ ] 2.2 Exercise real text wait/sleep commands and a real party battle/control boundary with synthetic data and reload, plus managed-browser handoff/status and sleeping-target combat visibility without live LLM. Verify terminal retry/reconnect adds no second round, fatigue charge or aftermath and cap/HP/MP/SP behavior is unchanged.
- [ ] 2.3 Update `docs/game/commands.md`, `docs/game/command-reference.md` and command-doc regression expectations for terminal-only fatigue, zero-round all-sleep defeat and unchanged cap. Verify mounted syntax remains synchronized with its curated manifest.

- [ ] 2.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Integrated handoff gates

- [ ] 3.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [ ] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [ ] 3.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate settle-terminal-combat-fatigue --strict`; verify docs, deltas and real test evidence agree before handoff.
