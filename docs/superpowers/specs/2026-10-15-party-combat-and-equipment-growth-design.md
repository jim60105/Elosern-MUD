# Party Combat Commands and Equipment-Driven Growth

**Date:** 2026-10-15
**Status:** Five design sections approved in conversation; written specification awaiting user review.
**Scope:** Whole-party combat commands, round-scoped tactical actions, ratio mitigation, weapon damage multipliers, and confirmed party retreat or surrender. Runtime implementation has not started.

Players select commands for their own character and every eligible allied companion. The last member's confirmation submits the complete round automatically. Equipment provides physical numerical growth, while defensive choices exchange a member's action for a round-scoped benefit.

## 1. Authority and current behavior

This document explicitly amends the combat contracts in §6.3 of `2026-07-29-ai-mud-engine-design.md`. It replaces flat defense subtraction with ratio mitigation, replaces autonomous allied companion actions with player-issued commands, and replaces personal allied fleeing with a party retreat operation. It retains deterministic resolution and the existing state-owner boundaries.

It realizes the equipment-side physical-growth intent recorded in §3 of `2026-08-30-use-driven-progression-design.md`. The new factor is named **weapon damage multiplier**. Element affinity remains a practice-XP concept with its existing eligibility rules. No character weapon-affinity attribute or weapon-proficiency damage progression is introduced. Stored base traits remain literal values. Skill proficiency continues to provide access rather than a direct damage bonus.

The current `player-combat-session` specification sends one player request into a full round and supplies policy requests for companions. `world/rules/combat_session/policies.py` implements that provider boundary. `world/rules/combat_session/rounds.py` owns the enclosing transactional round and settlement path. These existing boundaries remain the integration points.

Damage settlement and monster-AI estimation share the pure scalar functions in `world/rules/combat/scalars.py`. Equipment magnitudes currently reside in `world/rules/rulebook/equipment_effects.yaml`; `world/skills/equipment.py` reads per-entity inventory and equipment storage.

## 2. Scope and exclusions

The player can issue every supported personal combat choice to each controllable party member, including skills, usable inventory items, and the new basic tactical actions. The same menu and validation behavior apply to each member using that member's actual capabilities. Existing free operations retain their cost semantics; opening a bag or inspecting a choice does not count as choosing a round action. Existing equipment operations remain free and invalidate affected previews or drafts for revalidation when they change relevant state.

Enemies retain autonomous policies. They do not gain Defend, Dodge, or Taunt as new basic actions. Existing enemy skills with defensive or evasive effects remain available. Shared damage arithmetic and equipment effects remain symmetric across both sides.

Out-of-combat companion inventory management, bilateral item-transfer UI, and companion equipment-management UI are excluded. In-combat item commands still use the selected member's own inventory. This exclusion does not remove the full combat item-use flow.

No charge, counterattack, or cover action is added. No shared party inventory, stat-training system, new physical level, or proficiency combat bonus is added. Detailed whole-party UI design follows the active combat UI proposals and is outside this document's layout scope.

## 3. Whole-party command collection

### 3.1 Commander, actor, and eligibility

The account-controlled player is the commander. Each selected party member is the actor for that member's command. Commanding a companion neither transfers the account puppet nor invokes the possession lifecycle.

The server derives the required actor set from authoritative session membership and the existing ability-to-act rules. Defeated, knocked-out, fled, absent, or action-forbidden members require no command and receive no automatic attack. Enemy participants are never client-commandable. A stale actor selection is rejected with a named reason.

A member's skills, costs, inventory, equipment, legal targets, and disabled reasons are queried for that member. SELF effects bind to that member. Skill resources and item consumption are charged to that member. The server validates ownership and capability independently of client menu contents.

### 3.2 Draft and automatic submission

Each session has one server-owned draft for the next round. It records the session identity, round revision, and at most one selected round command per required actor. Commands carry actor identity, action kind, and the action's existing payload data. Object references are reconstructed from validated identities rather than persisted as live objects.

Confirming a member's selection saves that draft entry. Before all required members have commands, the player may revisit and replace any entry. Selection does not roll dice, apply tactical effects, deduct resources, consume items, run upkeep, or advance time. Enemy decisions do not run while the player is editing drafts.

The last required member's confirmation automatically submits the complete draft. There is no separate whole-party confirmation step. The server re-evaluates membership and preflights every command against current state before starting the round. If validation fails, it reports the members needing new selections, retains other valid entries, and starts no actions or upkeep. Membership changes cannot cause an incomplete old draft to execute silently.

An encounter-starting selection may seed the initiating character's draft entry, but companions still require their commands before interactive resolution begins. Whole-party interactive commands must not be replaced by automatic overwhelm attacks. Existing encounter-specific opening-order policy remains explicit; ordinary round command-entry order never changes initiative.

### 3.3 Ordinary resolution

After all preflight checks pass, compute the normal initiative order once and activate accepted round-start tactical declarations. Each declaration consumes its actor's selected action. Remaining actors resolve their selected command at their normal initiative position. Enemy policies continue through their existing deterministic boundary, subject to active targeting constraints.

Final action validation still occurs at execution. If an earlier action makes a selected target invalid, the later command loses its action opportunity without changing targets, spending skill resources, or consuming its item. The round does not pause for a replacement command, and prior valid actions remain part of the round. Ordinary misses and other valid resolution outcomes retain their normal costs.

Upkeep and round-time accounting run once. Existing execution gates still suppress actors who become unable to act. There is no extra autonomous companion policy action after a commanded action.

### 3.4 Persistence and retry safety

Confirmed draft entries survive disconnect and process restart. Reconnect restores command-selection progress without supplying missing commands or advancing combat. A draft revision identifies the round being submitted. Repeated confirmation, concurrent stale requests, and network retries cannot execute that revision twice.

The existing outer transaction encompasses all round effects and resource changes, session metadata, draft consumption, and terminal settlement when applicable. On technical failure, durable state and touched Evennia caches return to their pre-round state; the accepted draft remains recoverable. Normal mid-round action invalidation is a consumed action opportunity within a valid committed round.

Round-start declarations are scoped to this round. They cannot persist as ordinary long-duration buffs after rollback, reconnect, or round completion. A completed round clears its declarations and selections before collecting the next round.

## 4. Basic tactical actions

All three actions cost zero MP and SP. Each replaces the member's other action for the round, has no cooldown, and may be used in consecutive rounds. Eligibility is checked before activation. Their effects begin before ordinary initiative actions and expire at round end. They cannot be stacked across rounds.

| Action | Initial effect | Limits |
|---|---|---|
| Defend | Reduce eligible resolved damage by 35% after normal damage calculation | Does not reduce damaging upkeep ticks or explicitly defense-bypassing damage; final hit floor remains 1 |
| Dodge | Add 25 to the defender's to-hit threshold | Applies only to attacks using a hit check; grants no damage reduction on a hit, initiative bonus, or flee bonus |
| Taunt | Constrain one enemy's single-target hostile actions to the taunter | No forced attack, target-range exception, area redirection, healing prohibition, or flee prohibition |

### 4.1 Defend and Dodge

Defend is a final reduction on eligible direct damage after its ordinary mitigation, riders, and authored magnitude have been calculated. Convert the reduced result to an integer by flooring, then apply the damage floor. A damage occurrence explicitly bypassing defense is exempt from Defend as well. Damage that merely has a low or zero defense target remains eligible.

Dodge changes the shared hit-margin calculation through a defender-side threshold adjustment. The resulting margin also feeds the existing solid-hit band. The raw-roll critical rule remains unchanged and still requires the attack to land. Attacks without a hit check receive no invented miss roll. Area attacks with individual hit checks apply Dodge independently to each affected member's check.

The 35% reduction and 25-point threshold adjustment are rulebook parameters and initial calibration values. They are evaluated together with ratio mitigation and equipment growth.

### 4.2 Taunt and selection constraints

Taunt selects one living eligible enemy. It needs no extra success roll. When that enemy chooses a single-target hostile action for which the taunter is a legal target, it must target the taunter. The enemy remains free to choose another legal action kind, including an area action, a self or allied benefit, or fleeing. Taunt never grants an action new range, recipient eligibility, or effect capabilities.

Apply this constraint to enemy legal-candidate generation and estimation as well as final execution. Do not select an unconstrained action and silently redirect its effects afterward. Hostile action classification must agree with the authoritative typed-effect classification used for action presentation.

If multiple members taunt the same enemy, the member appearing first in the already-computed initiative order wins. Do not roll initiative again or use command-entry order. If that taunter becomes knocked out, defeated, absent, or fled, the restriction ends; a losing declaration does not take over during that round. Subsequent enemy decisions use their ordinary legal-selection rules. Taunt does not cancel an action already resolved.

## 5. Damage and equipment growth

### 5.1 Shared ratio mitigation

Replace subtraction by a defense retention factor:

```text
attack_part = round(attack * roll_multiplier * coefficient
                    * matched_multiplier * weapon_multiplier)
defense_used = max(0, adjusted_defense)
retention = K / (K + defense_used)
base_amount = int(max(attack_part * retention + rider, damage_floor))
scaled_amount = max(scaled_magnitude(base_amount, scale), damage_floor)
amount = scaled_amount
if eligible_defending_target:
    amount = max(floor(scaled_amount * (1 - defend_reduction)), damage_floor)
```

The existing `round` behavior for attack_part and the existing half-up `scaled_magnitude` operation remain in use. The max-HP rider stays after ordinary defense mitigation. The base floor remains before authored scale and is reapplied afterward. Defend follows scale and retains the final floor of 1. A miss produces no direct strike damage.

For an explicitly defense-bypassing occurrence, use defense 0 and skip the Defend reduction. Negative adjusted defense is clamped to zero for this retention calculation, preventing a zero or negative denominator. Negative defense modifiers continue to reduce positive defense toward zero.

Ratio mitigation applies to physical and magic damage on both sides through the shared scalar boundary. Weapon multipliers apply only to physical damage. A physical skill carrying an element remains physical for this factor; elemental practice affinity does not enter the damage path.

`combat.yaml` owns finite positive K, initially 40, and the tactical-action constants. The following table describes only the ratio curve before integer conversion, riders, or Defend.

| Adjusted defense | Retained damage at K = 40 |
|---|---:|
| 0 | 100% |
| 20 | 66.7% |
| 40 | 50% |
| 60 | 40% |

K = 40 is an implementation calibration starting value. It is not evidence of balanced encounters. Finite-value and bounds validation occurs at the existing rulebook load boundary.

### 5.2 Weapon damage multiplier

Weapon multipliers are authored equipment values in `equipment_effects.yaml`, alongside existing flat attack additions. Runtime consumers read loaded values. They never derive the factor from rarity, skill proficiency, guild rank, or an affinity attribute. Equipment load validation extends the closed schema and rarity-budget checks to cover this new field. Malformed, non-finite, or out-of-budget declarations fail startup validation.

Use the main-hand weapon's declared multiplier. If the main hand is empty, use the off-hand weapon's multiplier. Empty hands or an item without a weapon damage bonus give 1.0. Multipliers grant no penalty below 1.0. Two weapon multipliers never multiply together. Existing off-hand flat adjustments and dual-wield passives retain their current behavior. A non-weapon in an occupied main-hand slot does not grant an off-hand fallback bonus.

The factor affects basic_attack and applicable physical skill damage, including existing multi-strike actions. It does not grant extra strikes, multiply healing, or amplify magic damage. Real weapons must receive authored values through the implementation's shared balance pass; merely adding a dormant field with every shipped weapon still neutral does not complete this feature.

No per-item multiplier table is approved by this document. The implementation must select and record actual values with calibration evidence before completion. This is an explicit balance-authoring deliverable, with the invariants and required evidence defined below.

### 5.3 Armor and calibration

Armor continues through existing defense, gauge-cap, and authored trade-off fields. No separate armor multiplier is introduced. Positive defense reduces damage monotonically through the ratio curve. Defend provides its independent round-scoped reduction.

Calibration covers player and enemy damage together. It must exercise basic attacks, representative physical skills, magical controls, defense bypass, conditional multipliers, max-HP riders, authored scales, and multi-strike attacks. Include the combined skill-coefficient, critical, weapon-multiplier, and strike-count budget. Rebalance authored magnitudes only where the observed combined results require it; do not globally weaken skills without evidence.

Use independent synthetic examples to prove arithmetic. For K = 40, pre-mitigation damage 60 against defense 20 yields 40 before other factors; Defend then yields 26. At the same defense, a 1.5 weapon multiplier on that physical pre-mitigation attack yields 60 before Defend. A magic control receives no weapon increase. These fixed examples establish factor placement independently of registry data.

Use real construction and committed reload for equipment-growth smoke evidence, and the existing human-combat calibration boundary for encounter evidence. Record initial and selected balance values with the observed outcomes. A basic attack below the old subtraction threshold must have a positive marginal response to an adequate attack or weapon improvement; integer rounding and the floor may still mask very small increases. Do not claim every point of improvement changes every hit.

## 6. Party retreat and surrender

Retreat and surrender are session-level party operations. They remain available independently of which member's personal menu is selected. Allied personal flee routes must resolve to the same confirmed party operation, with no personal-flee bypass in the skill list or text commands. Enemy fleeing retains its existing individual mechanism and AI policy.

Both operations require an explicit confirmation before mutation. The browser uses a confirmation window stating party scope and consequences. Text clients provide an equivalent explicit confirmation. Canceling preserves the entire draft and advances no time. Confirmation is bound to the active session and current round revision; stale or repeated confirmations cannot affect another round or session.

### 6.1 Retreat

Confirming retreat replaces all pending personal commands with a party retreat attempt. Before ordinary actions, roll once using the lowest adjusted agility among allied members able to act against the highest adjusted agility among living, present, non-fled pursuers:

```text
d100 + minimum_allied_adjusted_agility >= 51 + maximum_pursuer_adjusted_agility
```

Reuse the existing adjusted-agility query and flee constant source. Accuracy and the Dodge threshold bonus do not affect the test. With no pursuers, escape is automatic and requires no roll. If no allied member can act, use the ordinary defeat path.

On success, the whole party leaves combat. Enemies take no actions in that round, which still counts as one elapsed combat round. Knocked-out companions still present with the party are carried out and excluded from the agility minimum. This grants no healing or revival and does not relocate entities to an invented destination.

On failure, the whole party remains. Every allied action opportunity for the round is consumed; enemies act under normal initiative and capability rules, followed by ordinary upkeep. The attempt costs no MP or SP and grants no Defend, Dodge, or Taunt benefit. No prior draft action executes. The next round starts a fresh draft.

Success and failure are all-party outcomes. Do not leave a subset of allies in combat. Apply elapsed time and terminal session cleanup once through the existing settlement boundary.

### 6.2 Surrender

Confirming surrender discards pending personal commands and immediately enters the existing hostile-defeat or guild-exam FAIL settlement. It rolls no success check, simulates no extra enemy attacks, and adds no artificial combat round. Settle the already accumulated time once. Preserve the existing defeat aftermath and exam-specific policy. Surrender grants no new safe-exit or restoration privilege.

## 7. Interfaces and active UI coordination

The server owns commandability, actor-scoped choices, valid targets, draft state, round revisions, and submission results. The client renders these facts and sends a member identity with that member's selected action. Server validation never trusts an actor identifier as authorization. This replaces puppet-bound assumptions for SELF targeting and inventory queries within party combat.

Retain one command-card flow for all members. The later UI design covers actor switching, selection progress, revisiting commands, and party-operation confirmation windows. It reuses skill, item, magnitude, and stage-target selection rather than duplicating companion menus. A party member being commanded and a participant being targeted must be distinct concepts.

| Active change | Existing ownership | Coordination contract |
|---|---|---|
| webclient-combat-command-card-centred | One centred command card and its geometry; no behavior or protocol changes | Reuse that card; design whole-party controls after its presentation contract |
| webclient-combat-stage-target-picking | Stage selection of skill targets | Parameterize SELF and target context by the commanded actor; preserve the distinction between actor selection and target selection |
| webclient-combat-panel-v6 | Participant conditions and skill hostile/beneficial classification | Reuse its classifications; add a separately designed protocol revision for party-command facts instead of assuming v6 already contains them |
| Other active formation, figure-plate, defeated-foe, and cross-side-confirm changes | Stage layout, participant treatment, and target warning behavior | Consume their committed contracts without redefining geometry or removing warning checks |

Do not edit or merge these active proposals as a side effect of this design document. Subsequent OpenSpec planning must re-read their current artifacts, since they can change independently. Required protocol additions follow the project's versioned exact-field schema convention; no old/new protocol compatibility layer is added.

## 8. Component boundaries and implementation decomposition

The following are planning slices within this approved design, not newly created OpenSpec changes or permission to start implementation.

| Slice | Responsibility | Dependency and conflict boundary |
|---|---|---|
| Damage and equipment growth | Shared ratio arithmetic, weapon field and budgets, armor/weapon balance evidence | Changes scalars and equipment contracts; tactical damage reduction must use its final ordering |
| Whole-party command core | Actor authorization, persistent drafts, preflight, one-round submission, retry safety | Replaces allied policy requests at the provider boundary; shares session transaction and terminal cleanup with retreat |
| Tactical actions | Round-start declarations, Defend/Dodge arithmetic, constrained enemy selection | Depends on party-command semantics and shared damage ordering; touches AI estimation and candidate legality |
| Party exit operations | Confirmed retreat and surrender, shared party outcomes | Depends on draft cancellation and exactly-once settlement; preserves enemy individual flee |
| Whole-party client interaction | Actor-scoped choices, draft progress, reused card/targets, confirmation windows, text parity | Detailed planning follows active UI proposals and the command-core contract |

Damage work and command-core planning can be separated, but shared round-boundary and protocol files require an integration owner. Break slices into workday-sized OpenSpec changes when writing the implementation plan. Do not ship the assembled feature with missing companion item use, placeholder actions, or a client unable to submit a complete party round.

## 9. Verification and documentation

Behavior tests must establish independent outcomes. Cover command ownership, actor-scoped SELF binding and resource use, local inventory consumption, complete-draft automatic submission, edits before completion, stale membership, duplicate submissions, and reconnect restoration. Inject failure after relevant writes to establish round rollback and cache restoration.

Prove that a target invalidated by an earlier action causes no automatic retargeting or resource consumption while prior actions and elapsed round persist. Tactical tests must show round-start effects protecting a slow actor, expiry, no cross-round stacking, Taunt candidate constraints, multiple-taunter priority, and restriction removal after the winner falls. Estimator tests must agree with settlement for weapon factors, Dodge, Defend, and constrained targeting.

Party-exit tests must exercise confirmation cancellation, stale confirmation, the slowest-member check, carried knocked-out companions, all-party success, failure with enemy actions and upkeep, no incidental tactical benefits, surrender consequences, and exactly-once time settlement.

An actual runtime smoke must select commands for multiple actors, use one companion's own skill and inventory item, revise an earlier choice, trigger automatic resolution with the final selection, observe the next round, and restore an unfinished draft after reconnect. Exercise retreat and surrender confirmation cancellation and their committed outcomes in isolated encounters. Browser verification uses the actual UI surface after its dependent client work; text-client confirmation also needs an exercised path.

Implementation updates affected main-spec requirements through OpenSpec, using canonical traceability IDs. Update both player command documents for command syntax or availability changes, schema validators and fixtures for protocol changes, and shard manifests for added or moved tests. Run focused tests and the contract gate; logging changes additionally require observability lint with their focused tests. Full managed browser execution and full traceability evidence remain CI-owned.

No runtime verification is claimed by this design document. The document records approved behavior and the evidence required from later implementation.

## 10. Written-spec review gate

The user reviews this committed English specification before implementation planning begins. Approval of this written version permits the writing-plans workflow to produce the plan. No implementation skill, runtime code change, or UI scaffold is authorized during this brainstorming phase.
