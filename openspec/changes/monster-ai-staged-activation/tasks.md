# Tasks

## 1. Behavior and establishing evidence

- [ ] 1.1 Review all prerequisite reports, focused tests and complete warm p95 before selecting activation; verify the release evidence links every acceptance criterion.
- [ ] 1.2 Author independently justified intelligence for a small explicitly named registered variant set and mode overrides; verify real registry binding and all other variants remain legacy.
- [ ] 1.3 Run one affected real encounter using startup settings and record raw settlement/reload evidence; verify legal actions and unchanged stats/skills.
- [ ] 1.4 Demonstrate switch-back through a new session or restart with fixed-seed legacy smoke; verify action/dice/flee behavior, empty restart memory and ordinary exception boundaries.
- [ ] 1.5 Document expansion and affected-profile retuning operations with a new fingerprint; verify the release record includes exact commands, seeds, configuration and rollback evidence.
- [ ] 1.6 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [ ] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [ ] 2.2 Register any new world.rules.tests.test_monster_ai_activation module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [ ] 2.3 Run only affected Evennia labels using `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_activation` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [ ] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-staged-activation` and `.worktrees/monster-ai-staged-activation`. This proposal creates neither. Apply depends on monster-ai-manual-evidence. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
