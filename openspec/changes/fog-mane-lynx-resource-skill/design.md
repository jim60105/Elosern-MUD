# Design

## Context

See proposal.md for the user mandate and scope. Proposed authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §8 owns this species' literal decisions; §2–§3 define the common environment-independent contact contract. Existing `data_monster_abilities.py`/`assembly.py` already supply one registry slice; `monster_individual.py` validates/persists kit/profile references and `monster_behaviour.py` accepts affordable active damage composites. No runtime gate extension is required. The new values remain pending user approval.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and all other species edits except cumulative specification replacements required by this batch.

## Decisions

### Declaration and ordered execution

Append `mane_crosswind_pounce` labeled 鬃風佯撲 to the existing ROWS after previously delivered monster content without altering crocodile order/content. Declare ACTIVE/SINGLE, combat-only (`usable_out_of_combat=False`), ANY faction, `wind` element/group and ELEMENTAL_MAGIC taxonomy. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("fog_mane_lynx",))`. Prerequisites and cast_conditions are empty tuples; no passive exists.

Ordered effects are `damage:wind:physical` and `buff_apply:mane_misdirection`. Occurrence 0 policy is coefficient 1.0, ENEMIES, single ordinary strike. Occurrence 1 is coefficient 1.0, ENEMIES, requires_hit_from=0. All remaining EffectPolicy fields use their existing defaults. No GaugeTransferPolicy, state-magnitude, damage bypass, extra strike or environment predicate is used. Costs are literal `{"mp": 10, "sp": 5}`; normal affordability, effects-before-cost and rollback stay authoritative. Pure buffs were rejected because the existing policy selects damage shapes; magical damage was rejected because every tier has zero magic-power bands.

### Timed modifier content

Add buff `mane_misdirection` with duration 15 world seconds, stacking refresh, polarity debuff, modifiers empty, no tick interval/marker/round_order. Add combat-modifier id `mane_misdirection_accuracy`, when buff_active equals `mane_misdirection`, then `accuracy: -5`. This follows existing earth defense/accuracy and ice agility_flat mounts. A miss skips the debuff; any successful source hit qualifies, including absorbed HP damage. Refresh changes expiry without stacking the magnitude. Existing tick/removal infrastructure removes the modifier, with no new timer.

### Literal profiles and policy binding

Complete rows in HP/MP/SP/atk_phys/agility/defense/magic_power order are `wood_stalker` 115/30/20/20/20/10/0 (D), `trail_hunter` 165/50/30/25/22/12/0 (C). Only MP/SP change. Set active_skill_keys to (`mane_crosswind_pounce`,), passive_skill_keys empty, behaviour_profile_key `ambush_predator`. Owned order precedes basic_attack/flee. Existing profile is first_owned/lowest_hp/no-area/flee 0.20; YAML stays unchanged. First-owned was chosen to avoid stat-estimate ties or coefficient-blind policy comparisons. No variant skill gate or progression chain is needed.

### Environmental and prose boundary

Choose prose-only ecological conditioning, using the independent contact effect above. No fog/light/loose-stone precondition or rider is represented, and no description, habitat or request context becomes a fact. Exact edits are in authority §8: 將「能力依賴既有霧氣，乾燥、無霧的環境中優勢大幅減弱。」改為「聚霧依賴既有霧氣，乾燥、無霧的環境中聚霧優勢大幅減弱；近身時的鬃風佯撲仍可使用，命中後使對手短暫誤判動作，戰鬥不另計霧氣加成。」保留「牠仍有足跡、氣味與聲音，不能完全隱形、製造任意幻覺或瞬間移動。」

Change this species' private author explanation as recorded in the authority; retain unknown origin and conjecture. Update current public prose and implementation status in bestiary plus existing author guides. The stale module docstring's global six-ability deferral must become an honest list of delivered and still-deferred species after this change. Existing historical approval appendices and the approved 2026-10-09 document remain untouched. Alternatives requiring room facts were rejected because cast conditions have no environmental subject and room archetypes/ground-marker buffs do not supply these facts.

### Main-contract cutover and tests

The three registry MODIFIED blocks include this change and its predecessor's cumulative approved exceptions, retain all unaffected scenarios and original header match keys, and remove this species from deferral. The crocodile ecology MODIFIED block removes only the obsolete restriction on these now-approved species; no crocodile numeric/skill changes. Identity eligibility, skill effect model, skill registry, behavior profile and flee capabilities are consumed unchanged, not duplicated.

Extend existing registered species content/profile, kit construction, behavior/flee and resolver tests. Add `world.rules.tests.test_fog_mane_lynx_resource_skill` as a tagged data-contract production smoke with exact rules-b (index 2) ownership and test_data_freeze registration. Formally construct both variants; real provider/resolver sessions prove hit/miss, nominal resource changes, buff refresh/expiry, either-resource exhaustion/basic_attack, inclusive flee, late rollback and reload. Controlled synthetic opponent keeps the fight alive and clock recovery is isolated for nominal deltas. General behavior tests use synthetic identities/effects; shipped definitions/pools belong only to registered data contracts. Existing hunt selectors and all other rows remain pinned.

## Risks / Trade-offs

Environmental expectations differ from combat implementation; explicit published sentence edits disclose the unmodelled ecology and forbid numeric environment claims. Self guard/debuff refresh can extend a short modifier while resources last; test duration and no magnitude stacking. A smoke may end by defeat/flee before exhaustion; use controlled opponent/actor HP and deterministic rolls without bypassing production selection/resolution. Pool/cost estimates are pending literals, not calibrated difficulty evidence.

## Migration Plan

After explicit approval and listed predecessor completion, implement this single content unit and required docs/tests. New construction receives the approved row and kit; existing individuals retain state until authorized GM action. No automatic reset/migration/shim. Rollback reverts the content unit through the normal reviewed workflow, without recalculating persisted current gauges. No apply/archive/sync occurs during proposal authoring.

## Full-set critique disposition

The single full-set critique's valid-contact self-guard clarification was fixed in the crab/hare deltas and common authority; composite/audience citations and approval-record wording were clarified. The reported band blocker is rejected from the already-read monster_species.py:666–728 current hare HP30/55 at low and lynx HP115/165 at mid. Historical Previous HP values are not shipped current profiles. No band exceptions, other-species retuning or gameplay reruns are needed. This disposition makes no second-review or runtime claim.
