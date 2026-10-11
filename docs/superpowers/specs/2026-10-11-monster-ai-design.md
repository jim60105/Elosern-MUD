# Monster Combat AI Upgrade Design

**Date:** 2026-10-11
**Status:** Conversational design approved; written-spec review required before implementation planning.
**Scope:** Utility attack decisions, tactical support and coordination, and small manual validation with staged activation.

## 1. Product contract

Upgrade deterministic monster action selection without replacing combat settlement. A monster proposes an existing `ActionRequest`; the deterministic action resolver remains responsible for effects, resource payment, time, events, and rollback. Decisions require no LLM, network service, or third-party AI package.

The canonical Chinese term for `intelligence` is **智慧**. Intelligence is an authored integer in the inclusive range 0..100, specified separately for each registered monster variant. Species membership, threat tier, danger grade, ordinary/stronger classification, combat stats, and behavior archetype impose no intelligence range or ordering. Two variants of one species may have different intelligence. A numerically stronger variant may be less intelligent.

Intelligence changes tactical evaluation and selection stability. It never changes literal base stats, available resources, skill ownership, proficiency, initiative formulas, or effect formulas. Greater intelligence need not produce a greater encounter win rate when the monster lacks the abilities or strength to exploit better decisions.

Existing `legacy` behavior is an explicitly retained decision mode and rollback control, not a compatibility shim. Its target selection, skill order, flee priority, and dice sequence remain unchanged. Non-monster combatants retain the existing delegated policy.

## 2. Evidence and corrections to the handoff

The supplied `tmp/Elosern-MUD-Monster-AI-Implementation-Handoff.md` is the research and intent input. This temporary input is not required to understand the approved contracts below. Current code was inspected at baseline commit `99a69d31`.

| Boundary | Current evidence | Design consequence |
|---|---|---|
| Behavior configuration | `world/rules/monster_behaviour.py` accepts exactly four profile fields | Extend validation deliberately; do not merely add YAML values |
| Archetypes | `world/rules/rulebook/monster_behaviour.yaml` contains six, including `ambush_predator` | Preserve and evaluate all six rather than the handoff's five |
| Variant identity | `MonsterVariant` is a complete standalone registry record; runtime construction validates its species/variant pair | Join AI tuning to canonical variant keys; no inferred identity or override chain |
| Session adapter | `_enemy_policy()` currently rebuilds context after selection, converts targets with `list()`, and omits scale | Build context first; preserve shorthand semantics and scale end to end |
| Legal preview | Preview/submission validation do not execute every cast and interaction condition | Share the complete deterministic gates with the resolver before scoring |
| Round orchestration | Providers have two arguments; one actor can receive multiple action slots; overwhelm runs internal rounds | Provide explicit ephemeral round/slot identity at the execution boundary |
| Observations | Successful action logs remain local to the round loop until it returns | Add a transaction-local observation seam for same-round coordination |

The architectural source of truth remains [the engine design](2026-07-29-ai-mud-engine-design.md). Its true-trait combat and single-writer boundaries continue to apply. Monster decisions never use `disguised_stats`. Hidden player submissions are excluded from snapshots, RNG inputs, tactical memory, and traces.

## 3. Selected approach

Use a focused decision pipeline with typed snapshots, bounded candidate generation, explicit effect estimators, scoring, and independent sampling. Shared legal gates and scalar combat arithmetic prevent a second rules authority. Do not simulate effects by calling handlers, rolling resolution dice, or running the resolver on copied entities.

A centralized expansion of `monster_behaviour.py` was rejected because it would combine configuration, selection, estimation, and memory lifetime in one module. A generic dry-run skill simulator was rejected because it would require isolation of handler writes, reactions, and randomness across the complete combat engine.

## 4. Independently reviewable subprojects

| Subproject | Detailed design | Deliverable | Dependency |
|---|---|---|---|
| Attack decisions | [Attack design](2026-10-11-monster-ai-attack-design.md) | Strict tuning, legal damage candidates, variant intelligence, scoring, RNG, and resolver integration | Existing combat and registry contracts |
| Tactical support | [Tactics design](2026-10-11-monster-ai-tactics-design.md) | Healing, calculable control/buffs, focus/threat, and bounded in-process observation memory | Attack decisions |
| Manual validation and activation | [Simulation design](2026-10-11-monster-ai-simulation-design.md) | Reproducible small-sample report, performance evidence, and staged variant activation | Attack and tactical behavior |

These correspond to the handoff's PR 1+2, PR 3, and PR 4. OpenSpec proposals and implementation plans must split them further into coherent one-workday changes where necessary. A configuration-only change must not claim the attack feature is complete.

## 5. Configuration ownership

`world/rules/rulebook/monster_behaviour.yaml` remains the AI tuning source. Existing archetypes own decision mode, preferences, flee thresholds, and utility weights. A `variant_intelligence` mapping owns the explicit intelligence value for each tuned registered variant. An optional `variant_decision_mode` mapping selects `legacy` or `utility` for individual registered variants; otherwise the resolved archetype's decision mode applies. Missing archetype mode means `legacy`.

There is no archetype intelligence default, tier-derived intelligence, species-level inheritance, copied persistent intelligence trait, or individual GM override in this scope. Legacy variants need not acquire intelligence tuning to continue working. A variant selected for utility must have a validated value. Tier-only or unregistered monsters remain eligible for legacy but cannot silently acquire utility intelligence.

Runtime behavior resolution honors the actual stored `behaviour_tree` binding. Resolving intelligence must validate the registered species/variant pair; reading a variant string alone is insufficient. A session records the resolved profile, variant intelligence, and configuration fingerprint in process. Configuration is loaded and validated at startup, with no new hot-reload mechanism.

Restart clears the in-process state and tactical memory. An existing combat session reconstructs through its current record and adopts validated startup tuning. Exact cross-restart decision replay is claimed only when the complete configuration and memory starting state also match; no durable AI sidecar is added.

## 6. Intelligence and behavior axes

Let `i = intelligence / 100`. Immediate damage, useful healing, and archetype preferences supply baseline utility. Tactical terms for finishing, resource management, waste, control, and cooperation have their authored weights multiplied by `i`. This continuous scaling avoids abrupt capability bands.

Selection uses stable softmax with initial temperature `T = 1.25 - 1.17 * i`. This is initial tuning, not a permanent balance assertion. Equal scores yield uniform sampling. Invalid scores or configuration fail explicitly. No intelligence value may bypass a mandatory target, resource, ownership, or cast gate.

Archetype preferences remain distinct. They favor simple attacks for `instinctive`, weak-prey/focus for `pack_hunter`, direct pressure on strong enemies for `brute`, spell efficiency for `tactical_caster`, finishing and coverage for `apex_predator`, and single-target ambush for `ambush_predator`. These preferences never prescribe a variant's intelligence.

## 7. Memory and transactional lifetime

Cross-round tactical memory exists only in process. It retains observed resolved events for a bounded window and is keyed by session and stable monster identity. It survives ordinary battlefield reconstruction between submissions, but not server restart.

A transaction-local overlay receives already executed actions before the next decision. The outer successful commit publishes its bounded memory result; rollback discards it. Terminal cleanup wins over publication and discards memory only after successful commit. This covers normal settlement, flee, forfeit, recovery, and missing participants. Selection itself never writes entity state or committed tactical memory.

## 8. Validation scale and exclusions

The owner explicitly replaced the original 1,000 encounters per archetype with a small one-time manual check. The baseline is 24 encounters per archetype, 144 total, plus 128 paired selector seeds without running encounters. Detailed allocation and limits are defined in the simulation design. The manual report generator is never part of full test discovery or default CI gates.

Permanent tests cover consumer-visible defects and boundaries with small deterministic fixtures. Do not add source-text assertions, tuning approval tables, exact prose assertions, or Monte Carlo encounter campaigns to the suite.

No combat stat rebalance, new abilities, patrol state machine, durable tactical memory, per-monster GM editing, GM UI, cooldown mechanics, phase-switch mechanics, telegraphed attacks, behavior tree, or GOAP planner is included. Existing mechanics may inform estimates; new mechanics require their own design and approval.

## 9. Specification and delivery obligations

Implementation must amend current OpenSpec requirements so legacy-specific target/skill/dice contracts remain scoped to legacy, while utility receives its own legal, offline, variant-intelligence and replay contracts. Amend the old prohibition on round/overwhelm integration changes for the new ephemeral execution/observation seams. Source-layout and wording-only assertions do not establish behavior and must be replaced by substantive coverage when affected.

Update AI tuning/authoring documentation and changelog with each permanent feature. Register added test modules in the existing shard manifest. Player command documentation is intentionally unchanged unless an implementation proposal adds a command, which this design does not request.

## 10. Research provenance

The prior handoff selected utility AI after comparing [Arx II's NPC decision services][arxii], [Evennia's EvAdventure AI example][evadventure], and [Arx's combat target selection][arx]. These are supplied research references, not claims that their current branches were re-audited during this design. Borrow concepts, not their ORM model or combat formulas. No external implementation is a dependency.

[arxii]: https://github.com/Arx-Game/arxii/blob/main/src/world/combat/services.py
[evadventure]: https://github.com/evennia/evennia/blob/main/evennia/contrib/tutorials/evadventure/ai.py
[arx]: https://github.com/Arx-Game/arxcode/blob/master/typeclasses/scripts/combat/utils.py
