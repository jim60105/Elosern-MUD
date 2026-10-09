# Design

## Context

See proposal.md for the user mandate and scope. Proposed authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §6 owns this species' literal decisions; §2–§3 define the common environment-independent contact contract. Existing `data_monster_abilities.py`/`assembly.py` already supply one registry slice; `monster_individual.py` validates/persists kit/profile references and `monster_behaviour.py` accepts affordable active damage composites. No runtime gate extension is required. The new values remain pending user approval.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and all other species edits except cumulative specification replacements required by this batch.

## Decisions

### Declaration and ordered execution

Append `ridge_bracing_kick` labeled 固埂蹬擊 to the existing ROWS after previously delivered monster content without altering crocodile order/content. Declare ACTIVE/SINGLE, combat-only (`usable_out_of_combat=False`), ANY faction, `earth` element/group and ELEMENTAL_MAGIC taxonomy. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("ridge_burrow_hare",))`. Prerequisites and cast_conditions are empty tuples; no passive exists.

Ordered effects are `damage:earth:physical` and `self_buff_apply:ridge_brace`. Occurrence 0 policy is coefficient 0.8, ENEMIES, single ordinary strike. Occurrence 1 is coefficient 1.0, SELF, requires_hit_from=None. All remaining EffectPolicy fields use their existing defaults. No GaugeTransferPolicy, state-magnitude, damage bypass, extra strike or environment predicate is used. Costs are literal `{"mp": 10, "sp": 3}`; normal affordability, effects-before-cost and rollback stay authoritative. Pure buffs were rejected because the existing policy selects damage shapes; magical damage was rejected because every tier has zero magic-power bands.

### Timed modifier content

Add buff `ridge_brace` with duration 20 world seconds, stacking refresh, polarity buff, modifiers empty, no tick interval/marker/round_order. Add combat-modifier id `ridge_brace_defense`, when buff_active equals `ridge_brace`, then `defense: 3`. This follows existing earth defense/accuracy and ice agility_flat mounts. With a valid selected contact target, the caster gains guard even on a resolved miss; rejected or no-target requests grant nothing. A source-enemy-hit dependency would incorrectly intersect away the caster, as shown in action/routing.py's audience/hit intersection. The SINGLE/ANY composite precedent is data_martial_sword.py's true_sword_saint. Refresh changes expiry without stacking the magnitude. Existing tick/removal infrastructure removes the modifier, with no new timer.

### Literal profiles and policy binding

Complete rows in HP/MP/SP/atk_phys/agility/defense/magic_power order are `burrow_maker` 30/20/9/4/8/3/0 (F), `nest_guard` 55/30/15/11/6/6/0 (E). Only MP/SP change. Set active_skill_keys to (`ridge_bracing_kick`,), passive_skill_keys empty, behaviour_profile_key `instinctive`. Owned order precedes basic_attack/flee. Existing profile is first_owned/lowest_hp/no-area/flee 0.35; YAML stays unchanged. First-owned was chosen to avoid stat-estimate ties or coefficient-blind policy comparisons. No variant skill gate or progression chain is needed.

### Environmental and prose boundary

Choose prose-only ecological conditioning, using the independent contact effect above. No fog/light/loose-stone precondition or rider is represented, and no description, habitat or request context becomes a fact. Exact edits are in authority §6: 保留「牠們只能處理巢穴周圍的鬆土，無法鑽穿岩盤、城牆或石造基礎。」及正常洞道逃離限制，追加「受逼近時，牠會以土屬性力量穩住身體後蹬擊，短暫提高自身防禦；此招不需要挖洞，也不封鎖他人的移動或行動。」

Change this species' private author explanation as recorded in the authority; retain unknown origin and conjecture. Update current public prose and implementation status in bestiary plus existing author guides. The stale module docstring's global six-ability deferral must become an honest list of delivered and still-deferred species after this change. Existing historical approval appendices and the approved 2026-10-09 document remain untouched. Alternatives requiring room facts were rejected because cast conditions have no environmental subject and room archetypes/ground-marker buffs do not supply these facts.

### Main-contract cutover and tests

The three registry MODIFIED blocks include this change and its predecessor's cumulative approved exceptions, retain all unaffected scenarios and original header match keys, and remove this species from deferral. The crocodile ecology MODIFIED block removes only the obsolete restriction on these now-approved species; no crocodile numeric/skill changes. Identity eligibility, skill effect model, skill registry, behavior profile and flee capabilities are consumed unchanged, not duplicated.

Extend existing registered species content/profile, kit construction, behavior/flee and resolver tests. Add `world.rules.tests.test_ridge_burrow_hare_resource_skill` as a tagged data-contract production smoke with exact rules-b (index 2) ownership and test_data_freeze registration. Formally construct both variants; real provider/resolver sessions prove hit/miss, nominal resource changes, buff refresh/expiry, either-resource exhaustion/basic_attack, inclusive flee, late rollback and reload. Controlled synthetic opponent keeps the fight alive and clock recovery is isolated for nominal deltas. General behavior tests use synthetic identities/effects; shipped definitions/pools belong only to registered data contracts. Existing hunt selectors and all other rows remain pinned.

## Risks / Trade-offs

Environmental expectations differ from combat implementation; explicit published sentence edits disclose the unmodelled ecology and forbid numeric environment claims. Self guard/debuff refresh can extend a short modifier while resources last; test duration and no magnitude stacking. A smoke may end by defeat/flee before exhaustion; use controlled opponent/actor HP and deterministic rolls without bypassing production selection/resolution. Pool/cost estimates are pending literals, not calibrated difficulty evidence.

## Migration Plan

After explicit approval and listed predecessor completion, implement this single content unit and required docs/tests. New construction receives the approved row and kit; existing individuals retain state until authorized GM action. No automatic reset/migration/shim. Rollback reverts the content unit through the normal reviewed workflow, without recalculating persisted current gauges. No apply/archive/sync occurs during proposal authoring.

## Full-set critique disposition

Adopted the self-guard target-boundary finding: only affordable resolved casts with a valid selected contact target grant guard, including misses; rejected/no-target requests grant nothing. The ability delta adds an explicit rejection scenario. The SINGLE/ANY composite and audience/hit-intersection sources are cited above.

Rejected the reported pre-cutover band blocker because current monster_species.py:666–728 already carries hare HP30/55 at low and lynx HP115/165 at mid; the reviewer used the historical Previous HP column and wrong cat tiers. No gameplay checks were rerun to confirm it and no band exception is proposed. Approval-record clarification is in the authority §11. This is the disposition of the single full-set critique.
