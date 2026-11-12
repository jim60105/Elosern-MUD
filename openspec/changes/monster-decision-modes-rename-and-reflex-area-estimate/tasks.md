# Tasks

This is implementation work for one engineer-day, approximately seven hours including bounded report operations. Planning completion leaves all checkboxes unchecked. Only this change's planning files are authorized now. Later implementation uses the exact boundaries in `design.md`; do not implement unrelated AI improvements, new skills/stats or migrations.

## 1. Mode/configuration cutover (45 minutes)

- [x] 1.1 In `world/rules/monster_behaviour.py`, rename `DecisionMode.LEGACY/UTILITY` to `REFLEX/DELIBERATION`, mode-only helpers and `InvalidStateFallback.LEGACY` per the design rename map. Update every caller, literal mode fixture and diagnostic default, including `server/conf/settings.py`, `world/rules/combat_session/ai_tuning.py`, `world/rules/monster_ai/manual_campaign.py`, `world/rules/monster_ai/manual_reports.py` and their existing tests. Preserve mathematical `utility_weights`, scoring APIs and capability/requirement identities. Former values must raise the existing configuration error; no aliases.
- [x] 1.2 In `BehaviourProfile`, `_OPTIONAL_PROFILE_FIELDS` and `_load_behaviour_profiles`, add `reflex_temperature` with the conditional finite-positive non-boolean validation in design section 4. Set initial 10.0 only in the rulebook's four `highest_expected_damage` archetypes. Rename all archetype mode values to reflex and the six existing variant overrides to deliberation; preserve variant intelligence values, keys and all combat content. Extend existing `test_monster_behaviour_profile` and `test_monster_ai_tuning` fixtures for required/missing/invalid/unused temperatures and both new/old mode names.

## 2. Exact reflex metric and selection (100 minutes, depends on 1)

- [x] 2.1 Replace `_choose_skill`'s target-defense calculation with a single-pass primary-damage descriptor using `zip(skill.parsed_effects, skill.effect_policies)` and `DamageEffect`; reuse adjusted own-school stat reads. Compute exact A*c*R once per skill. Define the shared descriptor projection for fingerprinting from the same parser; do not evaluate extra occurrences, conditional damage, hit probabilities or settlement handlers.
- [x] 2.2 Refactor `_reflex_action` from the renamed legacy body to compare viable SINGLE and AREA authored kits together. Keep existing flee, seal-before-positional, Taunt and target metric/tie behavior. Empty SINGLE targets must not discard legal AREA. Preserve all-enemies shorthand. Remove the area flag's reflex role without changing deliberation area preference. Exclude basic_attack from authored options; first_owned picks the first usable authored kit without evaluating or drawing, and no authored option falls back to qualified basic_attack or None.
- [x] 2.3 Thread optional keyword-only `rng=` and recorded tuning into reflex sampling. For highest_expected_damage with multiple authored options, reuse `selection_seed_for`, `softmax_probabilities` and `sample_index` from `world/rules/monster_ai/selection.py`, with actual execution scope or canonical inspection snapshot and private Random(seed). Follow the existing `_deliberation_action` snapshot scope construction; no new seed encoding. Skip sampling for a single usable authored kit. Deliberation scoring, temperature and resolver behavior remain unchanged.
- [x] 2.4 Bump `AI_ALGORITHM_VERSION` 5 to 6, include profile reflex temperatures and canonical sorted primary-damage descriptors in `_tuning_fingerprint`, and update `_load_ai_tuning`/manual harness consumers. Extend synthetic mutation tests to prove independent algorithm/mode/temperature/coefficient sensitivity and insertion-order stability without asserting a literal hash.

## 3. Mechanism tests and focused verification (75 minutes, depends on 2)

- [x] 3.1 Extend `world/rules/tests/test_monster_behaviour_selection.py` and `test_monster_behaviour_policy.py` for independent known arithmetic (10*1.5*1=15; 10*1*2=20), primary-damage policy ordinal, physical/magic own buffs, ignored defender defense/agility, dead/fled/allied recipient controls, false area flag, single-enemy AREA and empty SINGLE versus usable AREA. Pin injected draws for observable selection, not a guaranteed maximum under every seed.
- [x] 3.2 In those modules and existing `test_monster_ai_selection.py`, establish increasing probability with exact E, equal-score uniformity, identical-seed replay, distinct round/slot seeds, inspection replay and unchanged combat RNG state. Use the fixed enumerated 0..199 seeds with synthetic E=(10,20), T=10: the stronger skill must occur more than 100 and fewer than 200 times. No live randomness or statistical retries. Assert first_owned makes no evaluation/draw, singleton authored kits always return their kit, and basic_attack is fallback only.
- [x] 3.3 Update changed assertions and names in existing policy/integration/determinism/golden/activation/flee tests, including `test_monster_ai_flee_scope` coverage for the `monster-flee-policy` delta. Preserve reflex flee priority before both RNG paths, deliberation's voluntary-flee exclusion and typed-invalid-state reflex fallback. Convert affected golden tier-map approval assertions into synthetic profile mechanism cases. Retain real authored-kit rider settlement, ordinary and overwhelm adapter smoke, restart-only rollback and DB/resolver failure boundaries. Keep existing `test_overwhelm_threshold` adjusted-defense estimator test unchanged except mode naming where needed. Annotate substantive changed tests with the existing canonical IDs listed in design section 6. No new modules or shard changes are expected; any actual module move/addition must update `.github/evennia-shards.json`.
- [x] 3.4 Run focused commands A and B below once the code/tests settle. Expected state is all focused tests pass, no weakened shipped-content assertions, unchanged deliberation numeric scores/temperature and unchanged overwhelm estimator arithmetic. Fix real failures in scope rather than replacing mechanism assertions with source scans.

## 4. Current documentation and spec handoff (45 minutes, depends on 3)

- [x] 4.1 Update `docs/development/monster-ai.md`, `monster-field-behaviour.md`, `adding-monsters.md` and the existing change-history section in `monster-ai.md`. Explain 本能模式 / 權衡模式, clean mode values, raw-unit reflex_temperature ownership, exact primary-occurrence output estimate, stochastic evaluating strategy versus deterministic first_owned, authored-kit fallback and the deliberately ignored terms. Correct stale activation-roster prose from current declarations without adding tests that pin the roster/copy.
- [ ] 4.2 Amend current authority `docs/superpowers/specs/2026-10-11-monster-ai-design.md` and its attack/tactics/simulation companion documents where mode labels or unchanged legacy skill/dice promises conflict. Leave archived OpenSpec changes historical. Human-review terminology and encounter interpretation against design's “Human review record”; do not add copy/markup tests.
- [ ] 4.3 Record the changed test-to-requirement/scenario handoff. At later archive sync, obtain canonical IDs again with `uv run --locked python -m tools.spec_traceability list`, review/add the new or changed test annotations, and run the authoritative post-sync gate without `--change`. All current deltas are MODIFIED with unchanged headings, so no guessed ADDED IDs are needed. This checkbox records the handoff obligation; it does not authorize archive during implementation or planning.

## 5. Fresh fingerprinted evidence (90 minutes, depends on 3 and 4)

- [ ] 5.1 Run each explicit manual command C below independently on its tool-owned fresh scratch DB. Regenerate selector, six named archetype campaigns and complete-policy performance JSON/Markdown at version 6. Each invocation is one existing selector, 24-encounter whole-archetype or performance operation and must remain under the local ten-minute bound. No scenario-batching option or aggregation workflow exists or is required by this plan; never substitute a full-suite/CI command. If a whole-archetype operation cannot meet the bound, report the runtime blocker without claiming partial acceptance or inventing tooling. Campaigns stay manual, never test-discovered or gate-triggered. Expected selector margin >=0.15, deliberation warm p95 <=50 ms, isolated dice, zero selected-illegal actions and all 144 encounter results with required replay inputs; no balance-certification claim.
- [ ] 5.2 Rebuild `docs/development/monster-ai-activation-evidence/activation.json` from validated startup/rollback tuning with `reflex_rollback`, current algorithm and independently derived fingerprints. Refresh every evidence link to freshly generated reports; never transplant hashes into old results. Update both evidence READMEs with exact commands, baseline, seeds, host and measured results. All files in design section 5's table must be current. Historical fingerprints may remain only as explicitly superseded history.
- [ ] 5.3 Run command D after rebuilding the record; save actual focused output to `focused-tests.txt`. Run proposal/repository gates E and save actual output to `gates.txt`. Expected activation tests confirm current report algorithm versions/fingerprints, real settlement/committed reload, current reflex rollback, no session hot reload and unchanged exception boundaries. Evidence capture must not fabricate logs or reuse an older fingerprint's acceptance result.

## 6. Final scoped handoff (15 minutes, depends on 5)

- [ ] 6.1 Run `openspec validate monster-decision-modes-rename-and-reflex-area-estimate --strict` and `uv run --locked python -m tools.contract_gate --change monster-decision-modes-rename-and-reflex-area-estimate` if not already captured after the last edit. Require zero validation warnings and a passing gate. Report exact checks, evidence paths, new startup/harness/rollback fingerprints and human-reviewed limitations. Stop without unrelated audits, broad test suites, migration, archive or compatibility work.

## Runnable acceptance commands

Create an external temporary env file `/tmp/mud-monster-reflex-test.env` containing exactly `MUD_TEST_SETTINGS=1` before Evennia commands; remove it after verification. Do not commit it. Commands are run from repository root with locked uv. Outputs must be captured from the actual commands.

### A. Core selection/configuration regressions

```sh
uv run --locked --env-file=/tmp/mud-monster-reflex-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_behaviour_profile world.rules.tests.test_monster_ai_tuning world.rules.tests.test_monster_behaviour_selection world.rules.tests.test_monster_behaviour_policy world.rules.tests.test_monster_ai_selection world.rules.tests.test_overwhelm_threshold
```

### B. Adapter, rider and retained decision boundaries

```sh
uv run --locked --env-file=/tmp/mud-monster-reflex-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_behaviour_integration world.rules.tests.test_monster_behaviour_determinism world.rules.tests.test_monster_behaviour_golden world.rules.tests.test_monster_ai_flee_scope world.rules.tests.test_monster_ai_estimation world.rules.tests.test_monster_ai_support world.rules.tests.test_monster_ai_coordination world.rules.tests.test_monster_ai_manual_reports
```

### C. Explicit manual evidence operations

```sh
uv run --locked python tools/monster_ai_manual_reports.py selector --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype instinctive --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype pack_hunter --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype brute --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype tactical_caster --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype apex_predator --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype ambush_predator --output docs/development/monster-ai-manual-evidence
uv run --locked python tools/monster_ai_manual_reports.py performance --output docs/development/monster-ai-manual-evidence
```

Do not invoke these during proposal validation. The campaign baseline is the actual implementation commit, obtained by the tool; the activation record must distinguish harness fingerprints from startup tuning.

### D. Current evidence and production smoke

```sh
uv run --locked --env-file=/tmp/mud-monster-reflex-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_activation
```

### E. Proposal/repository contract gates

```sh
openspec validate monster-decision-modes-rename-and-reflex-area-estimate --strict
uv run --locked python -m tools.contract_gate --change monster-decision-modes-rename-and-reflex-area-estimate
```

No browser, complete evidence verification or full Evennia/CI shard run is part of this focused change. No build or runtime test is claimed by the proposal itself.
