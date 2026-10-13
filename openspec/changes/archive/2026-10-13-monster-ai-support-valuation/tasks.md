# Tasks

## 1. Behavior and establishing evidence

- [x] 1.1 Extend owned support candidate expansion with current allegiance and effect-audience gates; verify mixed omitted allies, implicit self and hostile seal independence.
- [x] 1.2 Share healing/drain scalars and project payment before ordered effects; verify capped/full-HP recovery, conditional miss and actual-loss drain with independent known outcomes.
- [x] 1.3 Use immutable modifier projections for next-opportunity denial/output/defense/resource economy; verify duration timing, stronger/redundant buffs and no opportunity before expiry.
- [x] 1.4 Integrate baseline healing and intelligence-scaled marginal control; verify real useful heal and control through the production adapter with committed reload and no constant fabricated score.
- [x] 1.5 Update docs/development/monster-ai.md with this slice's implemented authoring/runtime contracts and add its release changelog entry; verify documentation matches the exercised fixtures, uses the canonical player-facing term and adds no command documentation.

## 2. Traceability and focused integration

- [x] 2.1 Generate IDs from the equivalent delta-applied tree and attach covers_requirement to substantive tests for every new or modified requirement; verify retired source-only assertions are replaced by behavioral evidence and current IDs remain valid.
- [x] 2.2 Register any new world.rules.tests.test_monster_ai_support module in exactly one .github/evennia-shards.json shard; verify ownership using the existing inventory/ownership gate and keep manual operations outside default discovery.
- [x] 2.3 Create a temporary env file containing `MUD_TEST_SETTINGS=1` and substitute its path for `<path>`. Run only affected Evennia labels using `uv run --locked --env-file=<path> evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_support` plus affected existing labels; deliver output demonstrating declared scenarios and production-path committed reload/fault cases where relevant. Use the single-token `--env-file=<path>` form, never an inline environment prefix or a separate `--env-file <path>` argument. Remove the temporary env file after verification. Do not execute full CI shards, full browser suites or automatic manual campaigns.
- [x] 2.4 Run relevant observability lint if facade/logging paths changed, strict change validation and `uv run --locked python -m tools.contract_gate`; deliver exact outputs and resolve behavioral failures without exemptions.

## Apply conventions

The downstream apply owner uses `feat/monster-ai-support-valuation` and `.worktrees/monster-ai-support-valuation`. This proposal creates neither. Apply depends on monster-ai-attack-selection. Shared conflict ownership is recorded in proposal.md. Archive/sync is a later workflow and is outside tracked implementation tasks.

## Apply dispositions

- `monster-ai-tactical-support` is a NEW capability, so its requirement IDs are absent from `openspec/specs/` until the archive workflow materializes the capability's main spec (the same pre-archive state every earlier slice of this roadmap was in). Task 2.4's `tools.contract_gate` therefore reports exactly those `unknown-requirement-id` entries and nothing else; the IDs were generated and verified against the equivalent delta-applied tree (`tools.spec_traceability check` with the capability spec materialized at its canonical path: 2166 requirements, 2166 covered, 0 uncovered, 0 errors), and the materialized file was removed again rather than synced.
- Requirement 2's `HP cost before self heal` scenario was restated to the settlement-faithful observable the merged `monster-ai-effect-estimation` contract allows: the actor's payment is projected before the ordered effects and is a real own-side loss, while the restoration stays capped at settlement's staging-time, pre-action gap. The alternative reading (re-clamping the heal against the post-payment gap) would credit recovery the resolver never applies and would contradict the merged estimator requirement.
- Post-implementation review dispositions (all folded into the implementation, each with a regression test in `world.rules.tests.test_monster_ai_support`): the probabilistic lock is now weighted by the probability settlement actually rolls (the largest declared `chance` among the added zero-action rules, read rule by rule from the matching half of the same engine, never an additive merge total); a gauge-regeneration scale is compared against its settlement reader's unit default, so a lock that multiplies regeneration by zero removes the whole regeneration instead of being indistinguishable from no rule at all; and the "capped by the merge" zero case is asserted with a full examination ceiling.
- Two MODIFIED requirement deltas were added (`monster-ai-utility-selection`'s score formula, `monster-ai-effect-estimation`'s conservative-limits and bounded-features requirements) because this slice changes the completed score's formula and stops treating a resolvable buff/control mount as an unknown benefit.
