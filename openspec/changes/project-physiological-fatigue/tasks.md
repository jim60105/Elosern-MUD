# Tasks

Worker: luna
Branch: `feat/project-physiological-fatigue`
Worktree: `.worktrees/project-physiological-fatigue`

## 1. Projection and protected removal

- [x] 1.1 Extend `world/rules/buffs.py`, `world/rules/combat_modifiers.py`, rulebook definitions and `world/rules/status_display.py` to project one fatigue stage atomically using existing public grant guards. Extend `world/rules/tests/test_buffs.py` with exact threshold/modifier, no-expiry, no-base-stat-rewrite and projection-fault behavior tests.
- [x] 1.2 Update shared external-removal eligibility and cleanse effect integration so negative/all/concrete selectors preserve physiological statuses and correct removal counts. Verify mixed ordinary/protected instances and dispel hooks using synthetic definitions in the buff tests; keep equipment/unique-source guard regressions green.
- [x] 1.3 Document physiological status protection and ordinary cleanse limitations in the existing `docs/game/command-reference.md` cast/status prose with matching `tests/test_command_docs.py` contract assertions.

- [x] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. Eligibility and presentation

- [x] 2.1 Update `world/rules/party_scope.py` acting-purpose authorization and existing action blocking to read actual voluntary/forced sleep. Extend `world/rules/tests/test_party_scope.py` and field-action tests to prove forged direct sleep actions reject with zero effects/time while lawful organizing remains available.
- [x] 2.2 Extend no-create status/member read models and existing status protocol/rendering mirrors to show subject identity, rounded reserve and textual restrictions without changing owner-keyed hybrid resources. Extend `web/webclient/presentation/tests/test_status_panel.py` with possessed-host/owner divergence and no-write reads; add relevant existing client tests for bad payload rejection and truthful fatigue labels.
- [x] 2.3 Update existing status/command documentation with exact threshold-display semantics. Verify reload reproduces action gates and buffs and documentation tests retain real command discovery.

- [x] 2.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Integrated handoff gates

- [x] 3.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [x] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [x] 3.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate project-physiological-fatigue --strict`; verify docs, deltas and real test evidence agree before handoff.
