# Monster Tactical Support and Coordination Design

**Date:** 2026-10-11
**Status:** Conversational design approved; written-spec review required before implementation planning.
**Parent:** [Upgrade roadmap](2026-10-11-monster-ai-design.md)
**Dependency:** [Utility attack decisions](2026-10-11-monster-ai-attack-design.md)
**Deliverable:** Legal useful healing, calculable control/buffs, observed focus/threat, and bounded in-process memory.

## 1. Preserve the decision boundary

Extend the attack candidate/estimate contracts rather than adding a second selector. Every chosen action still follows preview, shared complete legal gates, submission validation, and the existing resolver. No support behavior directly changes a gauge, grants a buff, pays a cost, or alters initiative.

Use the same explicit per-variant intelligence and archetype weights. Species, threat tier, stronger-variant classification, and difficulty do not constrain intelligence. Intelligence scales tactical considerations continuously; low-intelligence monsters may still select an obvious useful heal.

This subproject adds no new skills, state effects, cooldown system, phase progression, or delayed/charged action model. Only existing deterministic effect semantics are evaluated.

## 2. Support candidate expansion

Owned active healing, supported buff application, and supported hostile control enter the candidate pipeline. Apply the skill's actual allegiance and target gates; friendly support is not redirected by `lamb_seal`. `SELF` support estimates the actor, and no-target skills use existing implicit binding.

Mixed damage/heal/buff skills retain their submitted target plan. The estimator filters each effect's recipients through that plan and its actual binding rules. Do not sum an ally heal found in broad preview if the submitted plan omits that ally. Do not omit a self-bound effect merely because no explicit self target was submitted. Harmful ally damage and beneficial enemy healing reduce utility.

A full-HP heal is legal when the resolver allows it, but has no health-recovery benefit and incurs its actual cost/waste. Unknown harmless benefit is worth zero. Unsupported potentially harmful effects or unrepresentable mixed recipient semantics exclude that candidate with a specific reason; they do not prevent other supported actions or change player/legacy resolution.

## 3. Healing and combined effects

Use the resolver's scalar healing magnitude, proficiency, potency, scale, conditional modifiers, and drain/recovery rules through pure functions. Cap benefit by projected missing HP. Ordered effect estimates update projected HP locally between effects, without changing the actual entity.

A damage-dependent heal is weighted by the actual modeled prerequisite; no benefit is granted on an impossible or unmodeled successful-hit branch. For drains, credit recovery from projected actual target loss rather than requested loss. Costs paid before effects are accounted for, so a skill spending HP before self-healing is not evaluated as if its actor remained at initial HP.

Include immediate healing as an unscaled baseline feature. Finishing, cost, waste, control and teamwork retain continuous intelligence scaling. This keeps simple survival behavior available without pretending low intelligence has full tactical evaluation.

## 4. Calculable control and buffs

Evaluate only modifiers with supported pure semantics: changes to resolved action availability, accuracy/damage output, defenses, or resource economy that affect a concrete eligible beneficiary within the next action opportunity. Reuse the existing modifier compiler and rulebook bounds in a hypothetical immutable projection; do not install a buff or call its handler.

The estimation horizon is one action opportunity for each affected participant, respecting the existing duration/tick timing. Expired effects, already equivalent/stronger non-stacking effects, participants with no remaining opportunity before expiry, and fully capped effects have zero marginal benefit. Reapplying an effect cannot receive its full value repeatedly.

Action denial is the reduction in available legal action opportunities divided by baseline opportunities. Other supported buffs/control use the bounded change in estimated offensive health impact or prevented incoming health impact, normalized by the appropriate faction HP capacity. If the outcome depends on an unsupported reaction or condition, omit uncertain positive value and report the limitation. Unsupported harmful consequences exclude the candidate.

A generic name such as stun, fear, or shield does not establish value. An estimator needs the existing definition's concrete modifiers and timing. Support/control implementation is complete only when synthetic real effects establish useful selection and committed resolution; a placeholder estimate is insufficient.

## 5. Observed focus and threat

Focus uses already resolved allied hostile actions aimed at still-live opposing participants. It never uses submitted player intent or future teammate choices. Friendly healing does not count as an alternative non-strike enemy attack for displacement rules.

For each opponent, sum observed allied pressure within the memory window, then normalize by the maximum positive pressure among opponents; an empty history contributes zero. A multi-target candidate averages its per-opponent focus values, avoiding extra reward solely for duplicate recipients. Archetype weights decide how strongly focus influences selection.

Threat uses observed incoming damage and successful opposing healing/control impact, normalized by the corresponding current faction capacity and decayed by event age. It informs the target-preference component only for profiles that value threat; it does not replace mandatory targeting. Unknown or unobserved events contribute no threat.

Retain the established distinct archetypes. Pack hunters can focus an observed weakened target, casters can preserve resources or support allies, and ambush variants can prefer one opening without requiring identical global policy weights.

## 6. Event and memory contract

A compact immutable observation contains session, actual round, sequence, source stable ID/faction, skill or item identity when relevant, recipient stable IDs, and resolved public outcome magnitudes/status facts. It contains no pending requests, private prose, arbitrary entity references, or callbacks.

Capture successful ordinary skill settlement, item effects relevant to health/support, and round upkeep effects through the deterministic workflow. The round loop exposes resolved results to a transaction-local observation collector immediately after success and before the next provider call. Upkeep is observed at its actual execution boundary. Rejected/rolled-back actions are not successful observations.

Store one bounded session event ring, with per-monster eligible projections keyed by session and actor identity. This avoids copying a full event graph for every monster. Initial limits are the most recent three actual rounds and 128 observations per session, whichever expires first. Store no more than one compact outcome record per settled action/upkeep boundary, using bounded recipient summaries for large groups. Capacity loss is visible in the detailed trace.

Events are visible only to eligible participants in that battlefield. Death, escape, missing objects, or faction changes update the next snapshot's relevant projection; an old ID is not permission to target a missing opponent.

## 7. Transaction-safe publication and cleanup

Begin each actual round with a transaction-local overlay over committed in-process memory. Earlier completed actions in that overlay are visible to later decisions in the same round. Multiple actor actions use their real slot identity; overwhelm starts a new round scope for every internal round.

On the outermost successful transaction commit, publish the overlay's bounded final state. On rollback, discard it. Never publish directly from an inner savepoint while the enclosing player action can still fail. Direct non-session round execution uses its own real transaction boundary or explicitly isolated ephemeral scope; it must not mutate shared session memory without such a boundary.

A terminal cleanup token supersedes all earlier publication callbacks from that transaction. After commit, retire the session memory and pinned configuration; late callbacks cannot recreate it. On rollback, do not delete the prior committed session memory. Apply this ordering to normal victory/defeat, successful flee, forfeit, invalid-session recovery, and missing/deleted participants.

Use per-session commit sequence/generation checks so older callbacks cannot overwrite a newer committed overlay. Session hooks install once and do not leak into later rounds or exceptions. Observe and test nested transaction ordering explicitly.

## 8. Restart, repeatability, and access

Memory is deliberately volatile. Reloading a battlefield between submissions preserves process memory; restarting the server clears it. The restored combat session remains valid and begins with an empty tactical history and current validated startup configuration. No durable sidecar, ORM schema change, or `CombatSessionRecord` field is added.

A trace/report includes the initial observation snapshot needed for same-process replay. Identical state, observations, configuration and decision scope reproduce selection. Identical session IDs alone do not claim identical replay after a restart or tuning edit.

Expose diagnostic data through the existing programmatic trace/report seam. This design adds no GM command or UI. Ordinary operational events use the observability facade; compact IDs/summaries enter context, with detailed records in opt-in report artifacts.

## 9. Completed score

Use the attack design's bounded signed damage/healing features and normalization. The complete score is:

```text
U = w_damage * damage + w_heal * useful_healing
    + w_preference * preference
    + i * (w_kill * finishing + w_control * marginal_control
           + w_focus * observed_focus - w_cost * cost - w_waste * waste)
```

Resource-management and threat preferences do not grant capabilities. Invalid numeric features are diagnosed at the same typed boundary as attack decisions. Unknown effects do not receive fabricated scores.

## 10. Acceptance and focused evidence

Permanent synthetic mechanism tests establish capped healing, prerequisite-dependent support, actual-loss drain recovery, mixed target plans, self-bound effects, ally harm penalties, redundant/expired control, supported marginal buff value, and observed-only focus. Use independently known outcomes and untouched recipients rather than echoing registry definitions.

Integration evidence must show a real monster choosing and settling a useful support/control action, two monsters coordinating only after an observed action, and `lamb_seal` overriding a conflicting focus preference. Show different session IDs cannot share memory and repeated battlefield reconstruction does not erase the same session's committed history.

Inject faults after relevant action writes and before outer commit. Observe same-round visibility, rollback retaining prior memory, nested publication ordering, terminal cleanup winning over publication, forfeit/flee/recovery cleanup, and restart using an empty history. These are plausible state-transition regressions, not handler-wiring assertions.

Run only focused tests and production-path smoke locally. The manual report generator and small encounter campaign belong to the simulation subproject and stay outside default test discovery.
