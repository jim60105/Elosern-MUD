# Tasks

## 1. Behavior and establishing evidence

- [ ] 1.1 Define compact observation records and bounded session rings; verify three-round/128-record expiry and bounded recipients without entity/intent references.
- [ ] 1.2 Collect successful skill, item and upkeep outcomes immediately; verify later same-round providers and each overwhelm round see only already executed public outcomes.
- [ ] 1.3 Implement outer-commit publication, complete savepoint checkpoints and generation sequencing; verify faults after writes, inner/outer rollback and stale callback ordering. Verify checkpoints restore observations, terminal token, generation state and pending tuning cleanup after a caught savepoint failure.
- [ ] 1.4 Integrate commit-only terminal cleanup across settlement, flee, forfeit, recovery and missing participants; verify late publication cannot recreate memory. Set a terminal token inside a savepoint, roll it back, catch the fault, settle another action and commit the outer transaction; verify successful observations publish and failed terminal work cannot delete configuration/history.
- [ ] 1.5 Preserve history through reconstruction with current eligibility and clear it on restart; verify session isolation and no durable AI schema or record fields.
- [ ] 1.6 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [ ] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [ ] 2.2 Register any new world.rules.tests.test_monster_ai_memory module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [ ] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_memory` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [ ] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-observation-lifecycle` and `.worktrees/monster-ai-observation-lifecycle`. This proposal creates neither. Apply depends on monster-ai-attack-selection. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
