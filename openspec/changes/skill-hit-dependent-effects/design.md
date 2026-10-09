# Design

## Context

The approved authority is the monster resource-skill design sections 4 and 8. Current `world/rules/action/routing.py::_step5_effect_resolution` visits each occurrence and stages handler outputs; `_bind_resolved_effect` replaces trusted policy/source context. `world/rules/combat/damage.py::_handle_damage` performs existing hit rolls while staging and currently keeps `hit` in the damage closure and textual description. Gauge transfer computes actual removal during commit and credits that amount before later costs. `ActionResolver.resolve` appends costs/practice and uses the common snapshot commit. No prose-derived hit dependency exists.

## Goals / Non-Goals

Deliver a standalone shared dependency mechanism validated by synthetic skills, with no production crocodile content or eligibility dependency. Support other already-supported target effect kinds through routing. Do not add hit rolls, a persistent flag, event-prose parsing, a new effect engine or a global transaction/order redesign.

## Decisions

### Per-occurrence dependency authoring

Extend frozen `EffectPolicy` in effects/policies.py with an optional earlier damage occurrence index, for example `requires_hit_from`. Indices address ordered parsed_effects, not effect strings, so repeated identical damage effects remain distinguishable. Validate a strict non-boolean integer index, bounds, source-before-dependent order and typed DamageEffect source in `SkillDef` construction/registry validation. Existing policy normalization and collection lengths remain authoritative. Unsupported or contradictory references fail before play.

### Trusted typed result channel

Add a typed damage-hit outcome carrying source occurrence, stable entity identity and the hit verdict to the existing staged effect contract in action/contracts.py, or a typed handler result used by routing. Prefer a narrowly scoped optional result field on the current PendingEffect contract so existing handlers retain their common list result. `_handle_damage` emits it directly from `_to_hit` for each existing strike, before diversion adjusts HP loss. Do not infer it from PendingEffect.description, event logs or reaction signals, which have different semantics.

Routing owns a fresh occurrence-to-hit-target map per final invocation. Aggregate source strikes with OR per target, preserve identity by entity object/PK rather than display keys, and pass only the intersection of the dependent occurrence's already-planned audience and referenced hit set to its handler. The map is not persisted and never supplied by request context. Strip/replace any incoming trusted result keys at the binding boundary; handlers receive outcomes only through resolver-owned routing. A self audience cannot gain recipients absent from source hits. An empty dependency intersection skips its occurrence even when its audience is SELECTED, avoiding the existing empty-list branch's ambiguity.

Preflight validates structure and ordinary audience availability but never calls damage handlers, rolls dice or requires runtime outcomes to exist. A structurally valid dependency remains castable on preflight even though its source may later miss. Final invocation regenerates current outcomes. Supported target status effects reuse the same filter without handler-specific dependency branches.

### Settlement and practice remain existing behavior

Retain PendingEffect staging and `_commit` snapshot/restore surfaces. Hit outcomes are planning facts, not a new persistent surface; actual MP removal/recovery remains computed by canonical writers during commit, after preceding damage/diversion and before cost effects. A hit with zero residual HP damage qualifies. Do not revalidate target living status between source damage and the rider, since defeat settlement follows the action.

Preserve existing successful-action practice semantics, including a paid miss. Existing ordinary routed recipients remain the practice basis; dependency delivery must not add recipients or multiply claims. A failure restores all declared actor/target surfaces and releases claims through the existing resolver path. No global cost-order change occurs. Unconfigured skills are behavior-identical.

## Risks / Trade-offs

Existing textual event logs remain for presentation, but are never dependency evidence. Tests distinguish hit from HP loss and use duplicate display names to detect identity mistakes. Multi-strike aggregation can accidentally multiply a rider; exhaustive deterministic strike vectors verify one execution per target. Snapshot coverage must include transfer reactions and actor recovery; inject a late pending failure and compare all touched stores, including a same-tick practice retry.

## Migration Plan

No data migration or compatibility layer. Ship independently using synthetic consumers; existing declarations require no rewrite because absent metadata preserves semantics. Serialize after eligibility for shared-file safety, even though no logical dependency exists. Verify and archive before the production crocodile consumer. Rollback removes the isolated policy/result extension as a unit. See proposal.md for physical conflicts.
