# Tasks

Worker: luna
Branch: `feat/handoff-sleeping-party-control`
Worktree: `.worktrees/handoff-sleeping-party-control`

## 1. Verified contextual transition

- [x] 1.1 Add proposed candidate/query and confirmation orchestration in `world/rules/possession.py` around existing `enter_possession`, `release_possession` and transfer compensation. Extend `world/rules/tests/test_possession.py` for awake owner return, no automatic candidate, forged/stale member/session, no remote target and only-contextual combat exception.
- [x] 1.2 Implement compensated companion-to-companion transfer with existing verified session/puppet/lock/cmdset lifecycle and single account binding. Extend `world/rules/tests/test_possession_transition.py` with failure after first handback and after target puppet, proving complete old-binding/cache/location restoration and no draft/time changes.
- [x] 1.3 Wire after-commit sleep transitions to candidate offers only for the controlled body; include actual current fatigue and return/possess kind. Verify unselected sleep and owner wake never steal control, and deletion/dismissal/disconnect/reload use existing cleanup only.

- [x] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. Text and browser delivery

- [x] 2.1 Route text contextual handoff and browser action admission through authenticated account/session authority even when the body sleeps. Reuse `web/webclient/actions/exploration_actions.py` transition helpers and `presentation/ingress.py` epoch synchronization; extend possession presentation/adapter tests for stale selection, cancel, recovery and old-epoch response suppression.
- [x] 2.2 Use existing modal selection/focus conventions for candidate choices and text restrictions; add managed-browser keyboard handoff/status/return-to-owner/reload acceptance without live LLM. Verify a real command/control boundary plus injected transfer failure, with only explicit safe waiting when no candidate exists.
- [x] 2.3 Update `docs/game/commands.md`, `docs/game/command-reference.md` and `tests/test_command_docs.py` to document exact mounted handoff syntax, zero-time cancel and restricted combat exception; verify direct sleeping-body cast/item/movement remain rejected.

- [x] 2.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Integrated handoff gates

- [x] 3.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [x] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [x] 3.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate handoff-sleeping-party-control --strict`; verify docs, deltas and real test evidence agree before handoff.
