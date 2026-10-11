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

The accepted OpenSpec proposal decomposition of this roadmap, its dependency and conflict matrix, and the batch critique disposition are recorded in section 11.

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

## 11. Proposal decomposition and delivery matrix

This section decomposes the roadmap into ten OpenSpec changes. Attack behavior is complete only after the first five slices, tactical behavior after support, observation and coordination, and rollout after evidence and rollback.

### Dependency and conflict matrix

| Change | Prerequisites | Observable deliverable | Shared edit ownership |
| --- | --- | --- | --- |
| monster-ai-variant-tuning | None | Validate variant-authored intelligence and decision modes while leaving every production variant on legacy. | Shares monster_behaviour.py, rulebook YAML, profile tests and session tuning with attack selection and staged activation; apply those afterward. |
| monster-ai-legal-snapshots | monster-ai-variant-tuning | Create immutable no-write snapshots and share complete deterministic legality with settlement. | Shares action preview/gates and modifier readers with damage estimation and support valuation; serial apply when those extract scalar helpers. |
| monster-ai-bounded-candidates | monster-ai-legal-snapshots | Enumerate semantically legal, deduplicated damage plans under a hard proposal budget. | Shares candidate and target-plan modules with support valuation; support must extend this producer rather than create another one. |
| monster-ai-damage-estimation | monster-ai-legal-snapshots, monster-ai-bounded-candidates | Estimate supported attack health effects with settlement arithmetic and conservative outcome models. | Shares scalar effect settlement and estimation with support valuation; apply scalar extraction before support changes. |
| monster-ai-attack-selection | monster-ai-variant-tuning, monster-ai-bounded-candidates, monster-ai-damage-estimation | Complete production utility attack dispatch with independent sampling, real execution identity and diagnostics. | Shares policy/spec deltas, session policies, combat rounds and overwhelm with observation lifecycle; observation hooks apply after these scope changes. |
| monster-ai-support-valuation | monster-ai-attack-selection | Choose useful existing healing and calculable control through the shared utility selector. | Shares candidates, estimation and utility scoring with observed coordination; scalar support precedes focus scoring. No new ability or state-effect authoring. |
| monster-ai-observation-lifecycle | monster-ai-attack-selection | Collect same-round resolved observations with bounded transaction-safe volatile memory and terminal cleanup. | Shares combat rounds/overwhelm/session lifetime and tuning state with staged activation and attack integration; serialize those writers. Observation eligibility precedes coordination. |
| monster-ai-observed-coordination | monster-ai-support-valuation, monster-ai-observation-lifecycle | Score focus and threat from resolved eligible history without overriding mandatory target rules. | Shares utility scoring, traces and snapshot projections with support and observation lifecycle; apply after both interfaces are complete. |
| monster-ai-manual-evidence | monster-ai-observed-coordination | Provide isolated manual encounter, paired-selector and whole-policy performance evidence outside default tests. | Shares manual operations/report fixtures and documentation with staged activation; activation consumes these reports and must not run the campaign through ordinary gates. |
| monster-ai-staged-activation | monster-ai-manual-evidence | Enable a small named variant set only after complete evidence and demonstrate legacy rollback. | Shares rulebook YAML and AI authoring docs with variant tuning. No production activation can run before manual evidence; no code conflict with unrelated exploration or quest proposals. |

All changes can share .github/evennia-shards.json and release documentation; the dependency-order integration owner resolves those edits. Legal snapshots and candidate enumeration precede effect estimation. Support valuation and observation lifecycle are the only independent substantial slices after attack selection, but their shared snapshot/trace edits require one owner. No unrelated active change is a prerequisite or authorized edit target.

### Roadmap coverage

| Roadmap section in this document | Detailed-design section | Concrete owner | Establishing evidence |
| --- | --- | --- | --- |
| 1, 5, 6 | attack 2 | monster-ai-variant-tuning | Strict synthetic loader, actual binding, independently authored same-species variants, unchanged stats and all six profiles |
| 2, 3 | attack 3, 4 legal gates | monster-ai-legal-snapshots | No DB/handler/timestamp writes, public-only inputs, complete paired cast/interaction rejection, no candidate-proportional ORM work |
| 3 | attack 4 plans, mandatory ordering and budget | monster-ai-bounded-candidates | SELF/NONE/mixed/AREA scales, semantic dedup, seal-before-displacement, real hostile alternative and hard rejected-proposal budget |
| 6 | attack 5 and 6 normalized features | monster-ai-damage-estimation | Independent scalar arithmetic, hit topology, ordered HP, conditional drain, conservative finishing and signed normalized costs/waste |
| 1, 6, 9 | attack 1, 7, 8, 9 | monster-ai-attack-selection | Production normal/overwhelm attacks, actual repeated slot identity, independent RNG, diagnostics, legacy dice and delta contract cutover |
| 6 | tactics 1 through 4 and 9 support terms | monster-ai-support-valuation | Real useful healing/control settlement, payment-before-heal, mixed audience, concrete marginal next opportunity and no fabricated score |
| 7 | tactics 6 through 8 | monster-ai-observation-lifecycle | Same-round skills/items/upkeep, nested/outer rollback, terminal cleanup order, reconstruction, isolation and empty restart memory |
| 6 | tactics 5, 9, 10 coordination | monster-ai-observed-coordination | Observed-only focus/threat, live eligibility, two-monster coordination, seal override and initial-memory replay |
| 8 | simulation 1 through 6 | monster-ai-manual-evidence | 144 real encounters, 128 paired seeds, six situations, isolated persistence, JSON/Markdown uncertainty and warm complete p95 <=50 ms |
| 9 | simulation 7, 8 | monster-ai-staged-activation | All-legacy starting state, evidence-gated named activation, real affected encounter, focused retuning and demonstrated mode rollback |

### Deliberately unchanged contracts

Monster flee thresholds, FLEE_SKILL_KEY and flee priority remain outside scoring. Non-monster delegated policy remains unchanged. Current effect definitions, base stats, initiative, resolver authority, true-trait arithmetic and transaction journals remain the existing product contracts. AI proposals amend legacy-specific main requirements through change-local deltas only. No durable memory, individual GM override, intelligence inheritance or entity trait copy is added.

### Startup-only mode transition

Every migration-plan reference to a new session means a session using configuration already loaded and validated at process startup. A fresh mode edit on disk requires restart before production rollback smoke. Terminating a session does not reload tuning, and this decomposition authorizes no hot reload.

### Batch critique disposition

The single blocking rubber-duck review covered all ten complete artifact sets and approved designs. It identified two blocking planning defects. Staged activation now requires restart to load an edited rollback mode and tests that a new session cannot reload disk edits. Observation lifecycle now checkpoints all publication controls, including terminal tokens and pending tuning cleanup, and tests a caught terminal savepoint failure followed by successful outer commit.

The review also identified an undefined threat-participation mapping. Coordination now uses the existing highest_effective_power strategy for utility threat participation, averages static-power and observed-threat ranks and verifies a paired nonparticipating lowest_hp profile. No new configuration field is added. These corrections preserve full approved scope; they do not constitute implementation evidence or a second independent review.
