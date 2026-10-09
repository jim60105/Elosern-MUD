# Design

## Context

See proposal.md for the user mandate and scope. Proposed authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §5 owns this species' literal decisions; §2–§3 define the common environment-independent contact contract. Existing `data_monster_abilities.py`/`assembly.py` already supply one registry slice; `monster_individual.py` validates/persists kit/profile references and `monster_behaviour.py` accepts affordable active damage composites. No runtime gate extension is required. The new values remain pending user approval.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and all other species edits except cumulative specification replacements required by this batch.

## Decisions

### Declaration and ordered execution

Append `lamp_carapace_claw` labeled 燈甲螯擊 to the existing ROWS after previously delivered monster content without altering crocodile order/content. Declare ACTIVE/SINGLE, combat-only (`usable_out_of_combat=False`), ANY faction, `light` element/group and ELEMENTAL_MAGIC taxonomy. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("tide_lamp_crab",))`. Prerequisites and cast_conditions are empty tuples; no passive exists.

Ordered effects are `damage:light:physical` and `self_buff_apply:lamp_carapace_guard`. Occurrence 0 policy is coefficient 1.0, ENEMIES, single ordinary strike. Occurrence 1 is coefficient 1.0, SELF, requires_hit_from=None. All remaining EffectPolicy fields use their existing defaults. No GaugeTransferPolicy, state-magnitude, damage bypass, extra strike or environment predicate is used. Costs are literal `{"mp": 10, "sp": 3}`; normal affordability, effects-before-cost and rollback stay authoritative. Pure buffs were rejected because the existing policy selects damage shapes; magical damage was rejected because every tier has zero magic-power bands.

### Timed modifier content

Add buff `lamp_carapace_guard` with duration 20 world seconds, stacking refresh, polarity buff, modifiers empty, no tick interval/marker/round_order. Add combat-modifier id `lamp_carapace_guard_defense`, when buff_active equals `lamp_carapace_guard`, then `defense: 2`. This follows existing earth defense/accuracy and ice agility_flat mounts. The caster gains guard even on a resolved miss; a source-enemy-hit dependency would incorrectly intersect away the caster. Refresh changes expiry without stacking the magnitude. Existing tick/removal infrastructure removes the modifier, with no new timer.

### Literal profiles and policy binding

Complete rows in HP/MP/SP/atk_phys/agility/defense/magic_power order are `shore_walker` 30/20/9/5/4/5/0 (F), `reef_warden` 60/30/15/12/4/7/0 (E). Only MP/SP change. Set active_skill_keys to (`lamp_carapace_claw`,), passive_skill_keys empty, behaviour_profile_key `instinctive`. Owned order precedes basic_attack/flee. Existing profile is first_owned/lowest_hp/no-area/flee 0.35; YAML stays unchanged. First-owned was chosen to avoid stat-estimate ties or coefficient-blind policy comparisons. No variant skill gate or progression chain is needed.

### Environmental and prose boundary

Choose prose-only ecological conditioning, using the independent contact effect above. No fog/light/loose-stone precondition or rider is represented, and no description, habitat or request context becomes a fact. Exact edits are in authority §5: 保留「牠們只能重現已有光源的節奏，不能製造幻覺或偽裝物體。」將「發光不等於治療能力，也不表示牠們掌握光屬性治療術。」改為「牠會在螯擊時收緊甲殼，短暫提高自身防禦；這項動作不依賴光源，發光斑紋與螯擊皆無治療效果，也不屬於光屬性治療術。」

Change this species' private author explanation as recorded in the authority; retain unknown origin and conjecture. Update current public prose and implementation status in bestiary plus existing author guides. The stale module docstring's global six-ability deferral must become an honest list of delivered and still-deferred species after this change. Existing historical approval appendices and the approved 2026-10-09 document remain untouched. Alternatives requiring room facts were rejected because cast conditions have no environmental subject and room archetypes/ground-marker buffs do not supply these facts.

### Main-contract cutover and tests

The three registry MODIFIED blocks include this change and its predecessor's cumulative approved exceptions, retain all unaffected scenarios and original header match keys, and remove this species from deferral. The crocodile ecology MODIFIED block removes only the obsolete restriction on these now-approved species; no crocodile numeric/skill changes. Identity eligibility, skill effect model, skill registry, behavior profile and flee capabilities are consumed unchanged, not duplicated.

Extend existing registered species content/profile, kit construction, behavior/flee and resolver tests. Add `world.rules.tests.test_tide_lamp_crab_resource_skill` as a tagged data-contract production smoke with exact rules-b (index 2) ownership and test_data_freeze registration. Formally construct both variants; real provider/resolver sessions prove hit/miss, nominal resource changes, buff refresh/expiry, either-resource exhaustion/basic_attack, inclusive flee, late rollback and reload. Controlled synthetic opponent keeps the fight alive and clock recovery is isolated for nominal deltas. General behavior tests use synthetic identities/effects; shipped definitions/pools belong only to registered data contracts. Existing hunt selectors and all other rows remain pinned.

## Risks / Trade-offs

Environmental expectations differ from combat implementation; explicit published sentence edits disclose the unmodelled ecology and forbid numeric environment claims. Self guard/debuff refresh can extend a short modifier while resources last; test duration and no magnitude stacking. A smoke may end by defeat/flee before exhaustion; use controlled opponent/actor HP and deterministic rolls without bypassing production selection/resolution. Pool/cost estimates are pending literals, not calibrated difficulty evidence.

## Migration Plan

After explicit approval and listed predecessor completion, implement this single content unit and required docs/tests. New construction receives the approved row and kit; existing individuals retain state until authorized GM action. No automatic reset/migration/shim. Rollback reverts the content unit through the normal reviewed workflow, without recalculating persisted current gauges. No apply/archive/sync occurs during proposal authoring.
