# Tasks

## 1. Authoring and trusted outcomes

- [x] 1.1 Add optional earlier-damage occurrence dependency to effects/policies.py and registry/vocab.py validation; extend effect-policy tests with negative/noninteger/boolean/self/forward/out-of-range/non-damage and repeated-ID cases, and document occurrence indexing in docs/development/adding-spells.md; verify malformed authoring fails before play and absent metadata preserves existing skills.
- [x] 1.2 Add typed occurrence/target hit evidence to action/contracts.py and emit it directly from existing rolls in combat/damage.py, without changing hit or damage formulas; extend damage-handler/divert tests and document hit-versus-HP-loss semantics in adding-spells.md, verifying one source strike has exactly one roll and fully diverted/absorbed hits still qualify.

## 2. Invocation-local routing and atomicity

- [ ] 2.1 Implement resolver-owned per-invocation aggregation and audience intersection in action/routing.py, skipping empty dependency intersections and replacing any forged trusted context; add synthetic world.rules.tests.test_skill_hit_dependencies registered exactly in rules-a (index 1), verifying per-target isolation with duplicate display names, all multi-strike hit/miss vectors, no extra roll, source occurrence independence, and reuse by an already-supported target status/buff effect; document recipient/any-hit semantics in adding-spells.md.
- [ ] 2.2 Keep preflight structure/audience checks dice-free without manufacturing outcomes and final outcomes local to each invocation; extend action-preview and preflight tests and existing guide, verifying forged caller data and an earlier action/round hit cannot qualify a new miss while dependency-free behavior is unchanged.
- [ ] 2.3 Preserve staged effects-before-cost payment, practice and snapshot surfaces; extend action-pipeline atomicity/audience and test_gauge_transfer coverage, verifying a miss skips transfer while paying costs and a late failure restores actor/target gauges and other touched state and releases same-tick practice claims. Document that dependency does not recheck post-damage living state or reorder existing settlement.

## 3. Integration acceptance

- [ ] 3.1 Run focused test_skill_hit_dependencies, damage handler/divert/multi-strike, effect audiences, gauge transfer, preview and action atomicity labels using the approved Evennia environment-file/test settings; record standalone synthetic-consumer evidence without eligibility/crocodile content and add requirement traceability markers for the future synchronized requirements.
- [ ] 3.2 Run uv run --locked python -m tools.contract_gate, applicable observability lint, data lint and openspec validate skill-hit-dependent-effects --strict; verify new module ownership and no species branches, new hit rolls, persistent flags or prose-derived success paths exist, and record exercised results.

## Workflow follow-up

- Verify/archive independently; recommended serialized apply/archive order places this after shared-skill-identity-eligibility for physical-conflict safety and before crocodile integration. No apply/archive is part of proposing.
