# Tasks

## 1. Behavior and establishing evidence

- [ ] 1.1 Extend the current loader and immutable profile records; verify malformed synthetic profiles fail and four legacy fields remain mandatory.
- [ ] 1.2 Validate variant references and actual behavior bindings at startup and runtime; verify untuned legacy and invalid utility identities have different outcomes.
- [ ] 1.3 Author optional modes, complete initial weights and budget with all production modes legacy; verify all six profiles resolve and no intelligence inheritance is present.
- [ ] 1.4 Record session tuning and fingerprint with startup/restart lifetime; verify no ORM schema change or entity intelligence attribute is written.
- [ ] 1.5 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [ ] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [ ] 2.2 Register any new world.rules.tests.test_monster_ai_tuning module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [ ] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_tuning` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [ ] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-variant-tuning` and `.worktrees/monster-ai-variant-tuning`. This proposal creates neither. Apply depends on no earlier batch change. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.
