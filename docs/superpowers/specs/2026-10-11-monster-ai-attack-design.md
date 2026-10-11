# Monster Utility Attack Decision Design

**Date:** 2026-10-11
**Status:** Conversational design approved; written-spec review required before implementation planning.
**Parent:** [Upgrade roadmap](2026-10-11-monster-ai-design.md)
**Deliverable:** A usable utility attack policy, corresponding to handoff PR 1 and PR 2.

## 1. Boundaries and responsibilities

`monster_behaviour_policy(entity, battlefield)` remains the public entry point. It delegates non-monsters unchanged, preserves the existing flee decision before combat selection, and dispatches registered monsters to their effective decision mode. Extract the current legacy body only as needed; do not change its branch order, skill order, target order, or dice consumption.

The utility package owns immutable decision data, candidate expansion, estimates, scores, sampling, and traces. Session/round orchestration owns ephemeral execution identity and observation lifetime. Existing rulebook validation owns authored tuning. Shared deterministic gates own legality. `ActionResolver` owns actual mutation and remains the final authority.

Keep files focused by responsibility, following existing repository style. Proposed boundaries are `models`, `candidates`, `estimation`, `utility`, `selection`, and `trace` under `world/rules/monster_ai/`. Tactical memory is a later consumer of the same immutable snapshot contract, not part of effect settlement.

## 2. Strict authored configuration

Preserve the four mandatory archetype fields and their existing validation. Add optional `decision_mode` and `utility_weights`. Default mode is `legacy`; utility weights have a complete named schema. Reject unknown fields, missing mandatory legacy fields, unrecognized modes, booleans used as numbers, negative or non-finite weights, and invalid primitive types.

Add top-level `variant_intelligence` and `variant_decision_mode` mappings to the existing YAML. Their keys must reference registered variant records with valid species relationships. Intelligence is a required explicit integer in 0..100 for every effective utility variant. The mode map is optional; a missing entry uses the actual resolved archetype mode. Validate all supplied intelligence values even for inactive legacy entries.

No archetype or tier supplies intelligence. Do not add species defaults, per-entity copies, a trait multiplier, or variant inheritance. Utility tuning does not make a tier-only monster registered. Such an object can use legacy; selecting utility without a valid identity and explicit intelligence is a typed invalid decision state and must be diagnosed.

Startup validation verifies authored references and utility activation coverage. Runtime resolution also verifies the actual `behaviour_tree` and species/variant binding because repair tools can alter stored data. The resulting immutable profile and AI configuration fingerprint are pinned for an in-process session. Fingerprints include decision algorithm version, variant intelligence, mode, weights, candidate budget, and relevant rulebook/skill estimation inputs.

## 3. Snapshot contract

A decision snapshot includes stable session/actor/participant identifiers, actual round and actor action slot, registry skill/variant identifiers, current resources, literal and effective combat traits, active buff projections, capability state, participant factions, resolved action context, and public settled observations.

Combat trait values follow the existing true-trait resolver path, never `disguised_stats`. No queued player action, unresolved teammate choice, event-handler object, mutable ORM entity graph, wall-clock timestamp, or Python object address enters scoring or seed construction.

Snapshot capture must use no-create read paths. Gauge reads do not regenerate resources or alter timestamps. Buff/stat reads do not initialize caches or attach handlers. Where current accessors perform such work, extract a shared non-mutating reader rather than accepting its side effects inside the snapshot.

Registry lookups, owned-skill metadata, current costs, participant traits, and buff projections are captured once per decision. Reuse those values across candidates. Do not use a cross-action cache that could conceal an earlier action's resource, health, or status changes.

## 4. Legal candidate generation

Start with owned active skills that contain supported hostile damage. Passive skills, unaffordable skills, and unsupported effects do not gain permission through scoring. Read the authored scale/target policy rather than assuming one damage effect or one recipient.

Use `preview_skill()` with the actual settlement context and candidate participants. Share the remaining cast, lineage, proficiency, interaction, capability, and target gates with the resolver through pure validation. Submission revalidation stays in place; the resolver repeats checks after initiative and earlier actions may change state.

The session adapter must construct normal or overwhelm context before policy selection. Round-level callers provide the same effective mode. Preserve `ActionRequest.targets` when it is a recognized shorthand and preserve `scale`; never convert a target string into a character list or drop a non-default scale.

### Target plans

For `SINGLE`, expand each valid target independently. For enemy-only `AREA`, create the actual legal group or existing `all-enemies` shorthand once. For `SELF` and `NONE`, use their existing binding rather than inventing an external target. Use current preview semantics for mixed-audience skills; do not assume every effect's broad recipient roster is actually submitted.

Mixed skills use a bounded set of semantically meaningful plans: the approved complete roster and the legal audience subsets supported by current target gates. At most one plan per distinct friendly/hostile audience combination is needed; do not enumerate arbitrary subsets. Self-bound effects are estimated on the actor regardless of external target omission. Reject plans that would apply an unsupported potentially harmful effect or whose audience effects cannot be represented consistently.

Deduplicate by canonical skill, scale, and sorted stable explicit target identifiers, expanding shorthands for identity comparison. Duplicate representations cannot increase sampling probability. Retain the correct runtime representation in the selected request.

### Mandatory ordering

Keep the legacy flee threshold and `FLEE_SKILL_KEY` unchanged and outside the scored attack pool.

For hostile single-target damage, first restrict to applicable `lamb_seal` bearers. If the actor lacks any genuinely castable non-strike hostile single-target damage skill, remove displaced targets. Then take the first remaining target in the existing canonical order. Having a non-strike self-heal does not satisfy the alternative-attack condition. Area attacks and friendly support are not restricted by this single-target seal rule.

A higher score cannot restore a removed target. Empty legal candidates return `None`. Do not force an attack or invoke legacy merely because utility found no legal candidates.

### Candidate budget

The initial budget is 256 deduplicated proposed candidates, configurable as a positive bounded integer. Generate deterministically and allocate slots round-robin across skill/semantic target-plan families after mandatory restrictions. Do not fill the budget from lexically early skill names alone. Within a single-target family, use the archetype's declared target ordering and stable IDs for ties.

Report budget exhaustion and omitted family/target counts. The bound limits proposals examined, including rejected proposals, so invalid candidates cannot cause an unbounded loop. Evaluate each distinct skill's broad preview once and reuse it when validating its target plans. The budget does not impose a game participant limit.

## 5. Explicit effect estimation

Estimators return signed per-recipient projected health effects, finishing potential, projected resource consumption, waste, and an approximation classification. They never roll dice, pay costs, call handlers, create buffs, or write events.

Share reusable scalar arithmetic with combat settlement for base damage, effect potency, scaling, mitigation, strike count, healing magnitude, and defined resource costs. Sharing scalar calculation does not mean running the settlement pipeline in a sandbox.

For supported ordinary damage, average the existing d100 outcome ranges analytically using rulebook values, with the actual hit-gate and multi-strike topology. Do not assume repeated strikes have independent hit gates if the resolver shares one. Track ordered per-target projections so later damage/healing effects see the projected remaining HP instead of independently claiming the full initial HP.

For reactions, diversion, conditional effects, and multi-strike interactions that cannot be represented exactly, use an explicitly labeled conservative estimate: omit uncertain beneficial conditional effects, subtract known shielding/diversion limits, and award finishing credit only when a supported outcome model or guaranteed-on-hit lower bound establishes it. Report these limits. No full encounter prediction is claimed. Unknown potentially harmful outcomes exclude the candidate; unknown harmless benefits contribute zero and appear in diagnostics.

Conditional effects use their actual prerequisites. A failed-hit branch must not receive unconditional healing, drain recovery, or buff value. Damage drained from a target cannot credit more recovery than projected actual loss. Current costs are evaluated at the candidate's scale and proficiency using the same read-only cost rules as settlement.

## 6. Normalized feature model

All feature magnitudes are in 0..1, with explicit beneficial/harmful signs for effect direction. Clamp projected values to remaining capacity; denominators of zero produce zero feature contribution. Let `H_enemy` and `H_ally` be sums of maximum HP over their eligible live factions, each bounded below by 1.

Damage benefit is projected effective HP loss of enemies divided by `H_enemy`; ally damage is a negative term divided by `H_ally`. Healing benefit is projected useful allied recovery divided by `H_ally`; enemy healing is a negative term divided by `H_enemy`. Current missing HP caps recovery. Waste measures unnecessary nominal health effect against remaining capacity, divided by total absolute nominal health magnitude.

Finishing is the supported knockout likelihood summed over hostile recipients, divided by the number of eligible live enemies. Do not award a certain kill merely because average damage exceeds current HP. Resource cost is the mean fraction of current spendable pools consumed, over pools charged by the skill. Include MP, HP, nutrition, and arousal under their actual spend rules; an unavailable pool was already rejected by legality.

Preference combines the configured target strategy, owned-skill preference, and area preference into a bounded score. Use a stable rank normalized over the relevant legal choices; ties share rank. It remains a soft bias in utility, while legacy retains its mandatory old ordering.

Let `i = intelligence / 100`. The completed attack score is:

```text
U = w_damage * damage + w_preference * preference
    + i * (w_kill * finishing - w_cost * cost - w_waste * waste)
```

Tactical support extends this same score with bounded healing, control, and focus terms. Every tuning weight is finite and non-negative. Non-finite estimated features or scores are typed invalid states, not values silently replaced by zero.

### Initial archetype tuning

These are initial authored values for manual validation, not permanent test assertions or claims of balance. Healing/control/focus activate with the tactics subproject. Intelligence is deliberately absent from this table.

| Archetype | Damage | Kill | Heal | Control | Focus | Cost | Waste | Preference |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| instinctive | 1.0 | 0.4 | 0.7 | 0.2 | 0.1 | 0.2 | 0.2 | 0.6 |
| pack_hunter | 1.0 | 1.6 | 0.8 | 0.5 | 1.2 | 0.35 | 0.5 | 0.4 |
| brute | 1.4 | 0.8 | 0.5 | 0.2 | 0.2 | 0.1 | 0.2 | 0.5 |
| tactical_caster | 0.9 | 1.2 | 1.4 | 1.0 | 0.6 | 0.7 | 0.8 | 0.3 |
| apex_predator | 1.2 | 1.8 | 0.8 | 0.8 | 0.8 | 0.4 | 0.6 | 0.3 |
| ambush_predator | 1.2 | 1.6 | 0.6 | 0.4 | 0.4 | 0.3 | 0.5 | 0.6 |

Use independently authored variant intelligence according to lore and observed tactics. No shipped content values are prescribed by a tier/rank table in this design. Manual validation may use synthetic variants of identical stats with intelligence 10 and 90.

## 7. Sampling and execution identity

Sort candidates by canonical skill key, normalized target identifiers, and scale before sampling. Use stable softmax with `Umax` subtraction and `T = 1.25 - 1.17 * i`, producing temperatures from 1.25 to 0.08. Reject non-positive/non-finite temperature; equal scores sample uniformly. Handle empty candidates explicitly.

Selection RNG lives in the utility selection module and is injectable. Production seeds use a versioned SHA-256 encoding of session ID, actual round index, actor stable ID, actual actor action slot, and pinned configuration fingerprint. Avoid Python `hash()`, unordered traversal, display names, ORM addresses, and shared combat dice. Repeating an identical decision scope reproduces selection without affecting hit, damage, or initiative rolls.

The round engine attaches ephemeral decision scope around every policy call. Multiple actions by one actor get distinct slot indices, and overwhelm supplies each actual internal round number. Restore scope on normal return and on exceptions. Preserve the two-argument provider contract.

A direct two-argument inspection call without execution scope uses canonical actor/participant IDs and a read-only snapshot fingerprint with slot zero. It never advances a hidden counter. It is reproducible inspection, not a substitute for the distinct slots required during a real round.

## 8. Diagnostics and error boundary

Detailed trace is opt-in for debugging/manual reports. It records scope, config/algorithm version, variant intelligence, seed, candidate/rejection counts, budget omissions, feature contributions, estimation limits, normalized target plans, and selected request. Full trace output uses explicit JSON report files or a programmatic result; normal facade context carries only a bounded summary.

Malformed tuning fails startup. A narrowly typed invalid runtime decision state emits a facade warning with available identifiers and exception context. The initial configured invalid-state behavior is legacy fallback; a diagnostic setting may select `None`. This fallback does not include empty legal candidates, unsupported individual candidates, late resolver rejection, database errors, or unexpected programming exceptions. Those keep their normal boundaries.

New logging paths use named facade imports and the existing exception policy. No console UI or player command is added.

## 9. Acceptance

Small deterministic regressions establish legacy action/dice behavior, identity validation, malformed tuning, skill ownership/cost/cast gates, mandatory seal/displacement ordering, mixed target/scale preservation, semantic deduplication, bounded enumeration, read-only snapshots, independent RNG, multi-action and overwhelm identity, and late resolver revalidation. Tests assert consumer-visible behavior, not private source layout or authored tuning numbers.

Smoke verification constructs synthetic registered monsters and opponents, selects utility through the production adapter, runs real settlement, and reloads committed resources/effects. Include a no-legal-action case and a fault after relevant writes. Run the focused labels, observability lint when its paths change, shard ownership gate for new modules, and repository contract gate.

The one-time 128-seed selector check is owned by the manual simulation design, not permanent full-suite discovery. Completion requires the end-to-end attack path; configuration parsing alone is not this deliverable.
