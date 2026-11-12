# Design

## Context

See `proposal.md` for motivation. `world/rules/monster_behaviour.py::_legacy_action` currently returns early for AREA, `_choose_skill` subtracts target defense and rolls combat dice on tied skill estimates, and `_damage_school` reads the first damage occurrence. `AI_ALGORITHM_VERSION` is 5. `_tuning_fingerprint` already includes both archetype and variant modes. The six archetypes are all `legacy`; six registered overrides select `utility`.

Existing `world/rules/monster_ai/selection.py` provides `softmax_probabilities`, `sample_index`, `selection_seed_for` and a private `Random(seed)` pattern. Real execution seeds use session/round/actor/slot/configuration; direct inspection uses canonical scope and the read-only snapshot fingerprint. No new RNG algorithm is necessary.

`EffectPolicy.coefficient` in `world/skills/effects/policies.py` is the authored per-occurrence coefficient, default 1.0. `DamageEffect` supplies school. `combat._adjusted_attack` owns the adjusted attacker read, including effective skill/passive and own buff contributions. Neither the reflex heuristic nor its sampling executes effects.

## Goals / Non-Goals

Implement the names and exact area-aware reflex skill comparison without changing resolution or deliberation valuation. Preserve `first_owned`, target metrics/tie dice, flee priority, mandatory seal/displacement/Taunt restrictions and non-monster delegation. Every candidate remains affordable and qualified; rejected SINGLE options cannot suppress an available AREA option.

No quantisation, expected-hit probability, target mitigation, HP clipping, reaction prediction, multi-hit simulator, conditional rider valuation, new skill/stat authoring, data migration or backward-compatible parser. No new test module is needed. Existing mathematical utility names and capability identities remain stable.

## Decisions

### 1. Clean rename map and boundaries

| Surface | Old | New |
| --- | --- | --- |
| `DecisionMode` member/value | `LEGACY = "legacy"` | `REFLEX = "reflex"` |
| `DecisionMode` member/value | `UTILITY = "utility"` | `DELIBERATION = "deliberation"` |
| `InvalidStateFallback` member/value | `LEGACY = "legacy"` | `REFLEX = "reflex"` |
| `MONSTER_AI_INVALID_STATE_FALLBACK` default/accepted mode | `legacy` | `reflex` (diagnostic `none` unchanged) |
| Archetype `decision_mode`, `variant_decision_mode` values | `legacy` / `utility` | `reflex` / `deliberation` |
| Mode-only helper names | `_legacy_action`, `_utility_action`, `_utility_dispatch`, `_validate_utility_coverage` | `_reflex_action`, `_deliberation_action`, `_deliberation_dispatch`, `_validate_deliberation_coverage` |
| Recorded rollback object | `legacy_rollback` | `reflex_rollback` |
| Chinese mode terms | prior mode descriptions | 本能模式 / 權衡模式 |

Keep field keys `decision_mode`, `variant_decision_mode`, `variant_intelligence`, `utility_weights`, `skill_choice`, `target_strategy`, and capability directories such as `monster-ai-utility-selection`. Utility describes the score's mathematics, so `UtilityWeights`, `utility.py`, utility-gap statistics and softmax feature names remain valid. Rename mode-specific report labels, fixtures, test names and consumer comparisons, including `manual_campaign.py`'s synthetic mode maps and performance labels. No alias members, dual accepted strings, conversion layer or persistent migration.

Audit mode consumers via `DecisionMode`/`InvalidStateFallback` references and literal mode values in `world/rules`, `server/conf`, tests and current AI documentation. Do not globally replace the mathematical word “utility”. Update current main-spec prose through these deltas; preserve requirement headings verbatim to preserve canonical IDs, even when a historical heading says “Legacy” or “one tie-breaking roll”. Archived changes remain immutable historical records.

### 2. Exact reflex score

For each usable authored SINGLE or AREA damage skill, compute

`E(s) = A(s) × c(s) × R(s)`.

`A(s)` is the actor's own adjusted `atk_phys` for the damage school's physical occurrence or adjusted `magic_power` for magic, including its own buffs. `c(s)` is the coefficient of the first damage occurrence in authored effect order, the same primary occurrence from which `_damage_school` currently chooses the school's stat. Iterate `zip(skill.parsed_effects, skill.effect_policies)` to obtain that `DamageEffect` and its policy together; never pair the first damage with policy index zero unless it is actually ordinal zero. `SkillDef._validate_effect_policies` already normalizes unspecified policies to identity 1.0. Additional damage occurrences, strike counts and conditional riders are deliberately outside this simple heuristic. No skills are rewritten to fit it.

`R(s)` is 1 for SINGLE. For AREA it is the number of distinct living hostile recipients in the action's enemy group, excluding dead/fled/absent combatants and allies. Preserve ordinary area targeting semantics, including displaced enemies. Do not limit AREA by SINGLE seal or Taunt restrictions. Use existing hostile/living roster semantics and emitted `all-enemies` targeting; do not infer hostility from names or variant identity.

Example with actor adjusted physical attack 10: SINGLE coefficient 1.5 gives 15; AREA coefficient 1.0 gives 10 against one enemy and 20 against two. An AREA with 20 receives higher probability than a SINGLE with 15 regardless of the old flag. It can still lose a draw. “Area chosen when better” tests pin a valid injected draw selecting its probability interval; no assertion demands that every seed choose the maximum.

The estimate ignores all defender defense/defense ratio, agility, hit chance, damage floors, critical/solid-hit ladders, defender buffs, elemental resistance, weapon multipliers and on-hit riders. These remain real settlement concerns. Preserve overwhelm `_expected_damage_per_attack` and deliberation `estimation.py` arithmetic, including their applicable defender terms. Read adjusted attacker values once per school per decision and calculate each skill estimate once; no sorting or copied battlefield per candidate.

### 3. Strategy and sampling contract

Filter usable authored damage skills first, excluding the innate `basic_attack`. “Authored” here means a qualified owned active damage skill whose key differs from `basic_attack`; do not invent a per-variant approval roster. Preserve `owned_keys()` order.

For `first_owned`, take the first usable authored skill of either shape, with no score evaluation or selection draw. For `highest_expected_damage`, compute all usable authored scores across both shapes, call `softmax_probabilities(scores, temperature=profile.reflex_temperature)` and sample via `sample_index`. Equal scores have equal probabilities. Owned order supplies the stable cumulative interval order; it grants no tie probability bonus. Use `Random(seed)` unless the keyword-only `rng=` seam supplies a generator. Thread this seam through `monster_behaviour_policy` and reflex selection only; keep existing callers valid.

Seed with existing `selection_seed_for(scope=current_decision_scope(), actor_id=stable_actor_id(entity), configuration_fingerprint=resolution.tuning_fingerprint, snapshot_fingerprint=snapshot.fingerprint)`. Reuse `DecisionReads` and `build_decision_snapshot` only when a stochastic reflex selection needs seed material; build its scope exactly as the current deliberation inspection path does. Do not change seed encoding or derive a seed from display names, addresses, Python hash, wall clock or hidden requests. Same state, ordering, tuning and scope replay the same request; different actual rounds/slots may choose differently. Independent selection RNG never advances combat hit/damage/initiative dice. Target tie draws retain their current contract; tests isolate skill selection from a target tie.

When no authored damage skill has a usable target and affordable resources, use the qualified innate `basic_attack` if legal; otherwise return None. With one usable authored kit, both strategies always return that kit. Skip sampling for a singleton. Flee remains the earlier inclusive-priority branch.

The supervisor selected this boundary because `first_owned` means no evaluation. `instinctive` and `ambush_predator` retain their deterministic single-kit/rider contracts. `pack_hunter`, `brute`, `tactical_caster` and `apex_predator` use stochastic evaluation. Sampling `first_owned` would make its name and `skill_choice` meaningless.

### 4. Temperature and area preference ownership

Add `BehaviourProfile.reflex_temperature: float | None` and optional profile field `reflex_temperature`. Require a finite positive non-boolean number on every `highest_expected_damage` profile, even if startup currently activates it only through deliberation, because it must be rollback-capable. It may be omitted for `first_owned`; validate a supplied value there too, with no effect on decisions. Author initial `reflex_temperature: 10.0` for the four evaluating archetypes, with a YAML comment that temperature is in raw `E` units and is initial tuning, not a fixed correctness constant. No intelligence multiplier/default or Python tuning literal. Deliberation continues `T=1.25-1.17*i` and never reads this new field for scoring or selection.

Remove `prefer_area_when_multiple_enemies` from reflex shape/skill selection entirely. Retain its key, loader validation and current deliberation preference ranking. This avoids changing deliberation scoring, and keeps exact equal-score reflex probabilities uniform. A reflex near-tie bonus would introduce a second score term and an unspecified threshold. Docs must explicitly mark this field as deliberation-only. AREA participates by `R(s)` even when the flag is false and even with a single enemy.

Refactor `_reflex_action` to form viable SINGLE and AREA options before strategy selection. Compute the SINGLE candidate domain with the existing seal, positional and Taunt ordering. If it is empty, discard SINGLE skills but keep AREA. Determine target-dependent SINGLE eligibility before scoring, retaining existing target strategy/draw behavior only when SINGLE options require it. Return AREA as `all-enemies`, SINGLE as an explicit one-target list. No area early return, except that `first_owned` can naturally choose its first viable AREA without evaluating stats. Preserve resolver authority and initiative-time revalidation.

### 5. Fingerprint and evidence cutover

Both renamed mode values and the changed metric/sampling contract invalidate tuning fingerprints. Bump `AI_ALGORITHM_VERSION` from 5 to 6. Include `reflex_temperature` in each profile fingerprint projection and include a canonical sorted primary-damage descriptor projection (skill key, primary occurrence ordinal, school, coefficient) for registered damage skills consumed by reflex, so coefficient edits cannot retain an acceptance fingerprint. Keep existing estimation/coordination leaves. Use synthetic mutation tests for independent sensitivity to mode, temperature and coefficient; no hardcoded expected hash.

The shared algorithm version and copied archetypes also move the manual harness fingerprint. The older activation note's “selector only” regeneration rationale does not apply. Regenerate from execution, never edit hashes into old results:

| Output | Required action |
| --- | --- |
| `docs/development/monster-ai-activation-evidence/activation.json` | Rebuild algorithm version, current startup fingerprint, `reflex_rollback` fingerprint, mode labels, exact operations and evidence links from current validated tuning and fresh smoke |
| Same directory `README.md`, `focused-tests.txt`, `gates.txt` | Record fresh focused output and current activation/rollback semantics; label all earlier hashes superseded |
| `docs/development/monster-ai-manual-evidence/selector-check.json` and `.md` | Rerun standalone selector at new startup fingerprint; unchanged deliberation gap/threshold |
| Same directory `archetype-{instinctive,pack_hunter,brute,tactical_caster,apex_predator,ambush_predator}.json` and `.md` | Explicitly rerun six 24-encounter operations under harness version 6; 144 total, no automatic all-profile loop in a gate |
| Same directory `performance.json` and `.md` | Rerun complete-policy comparison with `reflex`/`deliberation` labels and current harness tuning |
| Same directory `README.md` | Refresh baseline/operations/results; distinguish startup and harness fingerprints |

No trace sidecars currently ship; if a regenerated run exports `--detailed-trace`, its paired trace must match the run, otherwise do not add one. Historical documents and archived changes may retain explicitly historical hashes; none may be relabeled as current evidence. The activation record currently checks every referenced report's algorithm version, which is an additional reason to regenerate campaigns/performance after version 6.

### 6. Requirement identity and test handoff

Canonical IDs were obtained with `uv run --locked python -m tools.spec_traceability list --json-output /tmp/monster-mode-requirements.json`. All deltas are MODIFIED; no invented ADDED ID. Requirement and existing scenario headings stay stable, as required by strict scenario-preservation validation. Historical headings mentioning prior mode names, defense subtraction or a tie roll retain identity only; their rewritten WHEN/THEN bodies define the superseding behavior. The historical highest-expected-damage heading now describes a sampled metric in its requirement body; the historical shape heading now explicitly removes the early shape gate. Main requirements remain under 500 characters per body.

During implementation annotate substantive changed tests against existing IDs. During archive sync, re-list canonical IDs and annotate/review every new or changed test against the synced requirement and scenarios. Archive is not authorized by this planning request. Do not claim prose/copy approval or shipped roster echoes as behavior coverage.

| Existing canonical ID | Establishing tests to update/add within existing module |
| --- | --- |
| `monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll` | `test_monster_behaviour_selection`: exact synthetic score/probability ordering, equality/uniformity, replay and fixed-seed distribution |
| `monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected` | Same module: coefficient/ordinal/own-buff input, ignored defender state, deterministic first-owned and no selection effects |
| `monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the` | `test_monster_behaviour_policy`: one vs two enemies, dead/fled/allied controls, false flag, no viable SINGLE with viable AREA |
| `monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback` | Existing policy/integration tests: singleton authored kit always wins, exhausted/gated kits fallback, rider settlement unchanged |
| `combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math` | Selection tests plus existing overwhelm modifier tests: adjusted own physical/magic input; overwhelm defense retained |
| `monster-behaviour-profile::ai-tuning-is-strict-and-startup-scoped` | `test_monster_ai_tuning` / `test_monster_behaviour_profile`: old names rejected, new temperature bounds and conditional requirement |
| `monster-behaviour-profile::session-tuning-has-a-reproducible-lifetime` | `test_monster_ai_tuning`: independent mode, algorithm, coefficient and temperature fingerprint changes |
| `monster-ai-rollout::legacy-mode-rollback-is-demonstrated` | `test_monster_ai_activation.RollbackTests`: startup-only reflex rollback, flee/target behavior and new skill sampling boundary |
| `monster-flee-policy::utility-mode-never-voluntarily-flees` | `test_monster_ai_flee_scope`: deliberation excludes flee; only typed-invalid-state reflex fallback reaches its inclusive threshold |
| `monster-flee-policy::flee-selection-has-priority-over-attack-selection-without-consuming-decision-dice` | Existing flee tests: threshold flee precedes target draws and independent skill sampling |
| `monster-flee-policy::monster-flee-decisions-remain-deterministic-offline-and-yaml-tuned` | Existing flee tests: stored state fixes the flee boundary regardless of injected skill-selection RNG |

Other rename-only requirements retain their substantive existing tests, with enum/value fixtures updated. Extend existing `test_monster_ai_selection` numerical tests instead of duplicating the softmax engine.

### 7. Rejected alternatives

Bucket/step quantisation was rejected because two usable skills in the same bucket would always resolve to the first one, potentially repeatedly choosing the weaker skill. That is an ordering artefact, not cognition. Keep full numeric differences through softmax.

Deterministic maximum plus authored-kit/owned-order tie breaking was rejected after the user's correction: the user wants uncertainty. Seeded independent sampling solves the test reproducibility concern without removing imperfect choice. Combat d100 skill tie rolls were rejected because they perturb resolution RNG. Sampling the innate attack was rejected because a one-kit variant could abandon its authored attack and riders. Defender-faithful damage estimation and reusing deliberation's complete estimator were rejected because this change intentionally models only own power, authored potency and recipient count. Removing the area flag globally was rejected because it would change deliberation preferences.

## Risks / Trade-offs

Raw output units mean `reflex_temperature` has different practical sharpness across stat scales. Initial 10.0 is authorable and fingerprinted; synthetic tests prove mechanisms rather than freezing those shipped numbers. Stronger skills are more probable, never guaranteed. Primary-occurrence valuation intentionally omits additional/conditional damage and riders. These limitations must remain explicit in authoring docs.

A new algorithm fingerprint also changes deliberation seeds, so concrete draws can change while its scoring and temperature remain unchanged. Regenerated evidence establishes the new seed identity. Six existing manual campaigns are bounded at 24 encounters each; run each independently within the local ten-minute rule. No unresolved scope split is required because existing selection utilities and report operations are reused.

## Human review record

Review target is this document's rename map, stochastic boundary, raw-unit temperature rationale and evidence interpretation, plus the corresponding updates to `docs/development/monster-ai.md`, `docs/development/monster-field-behaviour.md` and `docs/development/adding-monsters.md`. Terminology/polish and encounter interpretation are human-reviewed, not executable requirements. Approval of this proposal authorizes the corrected design; implementation must record actual measurements, not a subjective combat-quality pass.

## Review disposition

The single blocking critique was `ProposeReflexModes.ReflexProposalDuck`. It found an omitted `monster-flee-policy` cutover, which is fixed by an additional MODIFIED delta, proposal capability entry and explicit changed-test handoff. The delta retains reflex flee priority, deliberation's voluntary-flee exclusion and typed-invalid-state reflex fallback, and scopes deterministic flee assertions to the predicate rather than subsequent stochastic attack selection.

The review also found that the report CLI has no scenario-batching option. Task 5.1 now cites only the existing explicit selector, whole-archetype and performance commands. No report batching API, aggregation workflow or extra tooling is claimed or planned. No findings were rejected or deferred. This critique establishes planning review, not implementation evidence.
