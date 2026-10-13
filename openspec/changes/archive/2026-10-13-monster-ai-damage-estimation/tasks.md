# Tasks

## 1. Behavior and establishing evidence

- [x] 1.1 Extract shared scalar damage/cost functions without changing settlement or legacy math; verify independent known hit-range, potency, mitigation and scale results.
- [x] 1.2 Implement analytic ordered recipient projections and shared-gate strike topology; verify capacity caps and no dice, handlers, costs or events.
- [x] 1.3 Classify exact and conservative models; verify shields/diversion, conditional miss branches, drain actual-loss caps and harmful unknown exclusions.
- [x] 1.4 Normalize signed damage, finishing, cost and waste; verify all resource pools, zero denominators and non-finite typed failures.
- [x] 1.5 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [x] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [x] 2.2 Register any new world.rules.tests.test_monster_ai_estimation module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [x] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_estimation` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [x] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-damage-estimation` and `.worktrees/monster-ai-damage-estimation`. This proposal creates neither. Apply depends on monster-ai-legal-snapshots, monster-ai-bounded-candidates. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
