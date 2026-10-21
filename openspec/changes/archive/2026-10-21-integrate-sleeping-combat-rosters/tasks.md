# Tasks

Worker: luna
Branch: `feat/integrate-sleeping-combat-rosters`
Worktree: `.worktrees/integrate-sleeping-combat-rosters`

## 1. Roster and activity evidence

- [x] 1.1 Update canonical `world/rules/combat_session/` engagement/reconstruction and required-actor/execution gates so present living sleepers stay roster targets without commands or automatic attacks. Extend existing `test_combat_session_targeting.py` and flow tests for sleeping owner plus awake companion, real incoming damage and unchanged HP-knockout semantics.
- [x] 1.2 Add validated initial-posture and explicit round-boundary activity evidence to `world/rules/combat_session/records.py` and snapshot restoration. Extend `test_combat_session_persistence.py` and recovery tests for reload/unfinished draft and a synthetic explicit wake boundary; verify no per-round reserve, buff-stage or clock update.
- [x] 1.3 Document terminal-only physiology and sleeping-command unavailability in existing combat command-reference prose and its command-doc tests; verify ordinary actor selection retains commander identity and actor-specific skills/costs.

- [x] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. AI and combat display

- [x] 2.1 Propagate sleep inability through existing monster observation and legal-candidate consumers while retaining ordinary target restrictions. Add synthetic enemy-choice behavior coverage at the owning monster tests and battlefield tests; verify sleeping targets remain legal and cannot be inferred dead/invulnerable or an automatic win.
- [x] 2.2 Extend the existing combat member presenter/client state to label sleeping/action-unavailable members separately from defeated members, retaining no-create query semantics. Verify existing client tests and managed-browser combat visibility/reconnect checks without new UI layout.
- [x] 2.3 Keep six-second rounds, 100-round cap and unrelated upkeep unchanged. Extend combat-flow regressions to prove a near-threshold sleeper never wakes in live rounds and nonterminal rounds do not settle world time.

- [x] 2.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Integrated handoff gates

- [x] 3.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [x] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [x] 3.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate integrate-sleeping-combat-rosters --strict`; verify docs, deltas and real test evidence agree before handoff.
