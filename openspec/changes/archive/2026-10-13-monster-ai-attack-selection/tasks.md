# Tasks

## 1. Behavior and establishing evidence

- [x] 1.1 Implement attack score, stable ranks and stable softmax with independent injectable RNG; verify numerical stability, equal scores and unchanged combat dice.
- [x] 1.2 Establish real ephemeral round/slot scope in normal rounds and each overwhelm internal round; verify repeated slots, nested exceptions and direct inspection replay.
- [x] 1.3 Integrate context-first dispatch and preserve targets/scale; verify real production-path attack, no-action and committed reload plus rollback fault.
- [x] 1.4 Preserve legacy dispatch, flee priority and non-monster delegation; verify fixed-seed action and dice regressions and amend all affected main-spec contracts with substantive tests.
- [x] 1.5 Implement opt-in trace and narrow typed facade warnings; verify errors outside the typed boundary propagate normally and hidden intent never appears.
- [x] 1.6 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [x] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [x] 2.2 Register any new world.rules.tests.test_monster_ai_selection module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [x] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_selection` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [x] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-attack-selection` and `.worktrees/monster-ai-attack-selection`. This proposal creates neither. Apply depends on monster-ai-variant-tuning, monster-ai-bounded-candidates, monster-ai-damage-estimation. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
