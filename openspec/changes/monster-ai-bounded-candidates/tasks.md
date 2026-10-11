# Tasks

## 1. Behavior and establishing evidence

- [ ] 1.1 Implement canonical semantic target plans and executable representation preservation; verify SINGLE, AREA, SELF, NONE, mixed roster subsets and scaled requests.
- [ ] 1.2 Apply seal and displacement rules using genuinely castable hostile alternatives; verify multiple seals, uncastable magic, self-heal and separate strike exclusions.
- [ ] 1.3 Deduplicate shorthand and explicit identities; verify duplicates cannot increase sampling probability.
- [ ] 1.4 Implement the bounded round-robin family ring and digest offset; verify rejected proposals count, exhaustion diagnostics and no extra RNG consumption.
- [ ] 1.5 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [ ] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [ ] 2.2 Register any new world.rules.tests.test_monster_ai_candidates module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [ ] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_candidates` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [ ] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-bounded-candidates` and `.worktrees/monster-ai-bounded-candidates`. This proposal creates neither. Apply depends on monster-ai-legal-snapshots. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
