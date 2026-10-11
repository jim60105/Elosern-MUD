# Design

## Context

See proposal.md for the mandate and approval history. Authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §8 owns this species' literals; §§2–3 define the shared contact contract, approved with the whole batch on 2026-10-10 in §12. Implementation remains pending. The generalization cutover at `8f33f414` makes profile obligations, kit delivery and identity authored registry data. Existing declaration, construction and policy APIs need no extension.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and other species data edits. Consume the generic contracts without modifying specs or restoring species-specific scenarios.

## Decisions

### Approved declaration and ordered execution

Append `mane_crosswind_pounce`, label 鬃風佯撲, to the existing monster ROWS after delivered content. Preserve existing order/content. Declare `SkillKind.ACTIVE`, `TargetSpec.SINGLE`, `usable_out_of_combat=True`, explicit `FactionConstraint.ANY`, element/group `wind` and `SkillCategory.ELEMENTAL_MAGIC`. The historical “combat-only” phrase describes contact action/targeting, with selection outside combat retaining the ordinary battlefield gate. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("fog_mane_lynx",))`; no race/subrace restrictions or required capabilities. `prerequisites=()` and `cast_conditions=()`; no passive or progression chain exists.

Ordered effects are `damage:wind:physical` and `buff_apply:mane_misdirection`. Occurrence 0 uses `EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES)` and no hit dependency. Occurrence 1 uses `EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0)`. All remaining fields retain existing defaults. No GaugeTransferPolicy, state magnitude, bypass, extra strike or environment predicate is used. Costs are `{"mp": 10, "sp": 5}`. Damage reads `atk_phys`; element is taxonomy and adds no magic-power scaling. Ordinary living/contact/positional target gates apply. ANY permits ally selection, while enemy damage/riders never reach an ally.

Affordability for both adjusted resources precedes dice/effects. A resolved hit or miss pays both costs once after effects; rejected actions write nothing and late failure restores gauges, buffs and practice claims. Existing resource modifiers, reactions and recovery remain unchanged. MP 10 retains the apprentice single-target cost classification; the composite remains freeform-ineligible.

### Approved timed modifier

Add `mane_misdirection` with duration 15 world seconds, `stacking: refresh`, `polarity: debuff`, `modifiers: {}` and no tick interval, marker or round_order. Modifier row `mane_misdirection_accuracy` has `when: {buff_active: mane_misdirection}` and `then: {accuracy: -5}`. A miss applies no target buff; a source hit qualifies even when HP damage is fully absorbed. Apply the contribution once to the selected hit enemy, with no caster/ally delivery. Refresh changes expiry without accumulating magnitude; expiry/canonical removal eliminates the modifier. No action lock, DoT, ground hazard or displacement is introduced.

`status_display.py` rejects missing buff/rule display codes at import. Add both codes to `world/rules/rulebook/status_display.yaml`, following the delivered enemy-rider precedent, with severity `harmful`. Use labels 鬃風佯撲 and 鬃風佯撲命中下降 for the buff and modifier respectively. These presentation labels derive from the approved ability/effect; they introduce no mechanic or change to the approved skill label.

### Approved complete rows and policy binding

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `wood_stalker` | 115 | 30 | 20 | 20 | 20 | 10 | 0 | D |
| `trail_hunter` | 165 | 50 | 30 | 25 | 22 | 12 | 0 | C |

Only MP/SP change. Preserve `profile_required=True`, species key `fog_mane_lynx`, variant keys, tier/default/ordinary membership, physical axes and grades. Both variants declare `active_skill_keys=("mane_crosswind_pounce",)`, `passive_skill_keys=()` and `behaviour_profile_key="ambush_predator"`. Owned order is special ability, innate `basic_attack`, innate `flee`; flee retains independent priority. Existing profile is `first_owned`, `lowest_hp`, area preference false, inclusive flee threshold 0.20. Behavior YAML stays unchanged. Exhaustion of either resource selects ordinary attack; final resolver gates remain authoritative after initiative changes state.

### Approved public/private prose and keyed status

Replace 「能力依賴既有霧氣，乾燥、無霧的環境中優勢大幅減弱。」 with 「聚霧依賴既有霧氣，乾燥、無霧的環境中聚霧優勢大幅減弱；近身時的鬃風佯撲仍可使用，命中後使對手短暫誤判動作，戰鬥不另計霧氣加成。」 in `published_ecology_zh` and the current bestiary ability boundary. Retain 「牠仍有足跡、氣味與聲音，不能完全隱形、製造任意幻覺或瞬間移動。」.

In `author_explanation_zh`, replace 「以環境條件（霧氣）限定優勢」 with 「以霧氣限定聚霧生態；近身佯撲及短暫命中干擾由鬃毛氣流與動作產生」. Retain hidden origin, unverified conjecture, habitat, ecological paragraph and variant direction. The independent contact action needs no measured fog fact; narrative and forged request context grant no effect.

Change the species and both variant statuses in this species' current keyed `bestiary` block from `narrative` to `delivered`, the checker's actual kit-backed status value, preserving keys, default/parent relationships and public-field links. Update current delivery notes for this species only. Historical approval appendices and the 2026-10-09/10 authorities remain unchanged. Existing author guides already describe generic content authoring; no guide edits or global species list are needed. This last batch member delivers the remaining kit through data without claiming environmental simulation.

### Existing contracts and minimal rule-correspondence work

No spec delta is needed. This change declares `skip_specs: true` and removes the old four capability deltas without replacement stubs. Current contracts cover complete declared profiles, validated kit references, shared effect/payment semantics, atomic construction, live-state preservation and keyed bestiary coverage. The archived cutover's `retained-contracts.md`, `cutover-matrix.md` and `wp7-integrated-acceptance.md` explain the retired approval tables/species scenarios and retained bounds/mechanisms.

`test_monster_species_content.py::ShippedProfileConstructionTests` constructs and reloads every live variant. `AuthoredMonsterKitContractTests` in `test_registry_contract.py` derives all kit references and checks kind, identity, cost/effect and hit/audience closure. `test_bestiary_documentation.py` checks keyed coverage/status and public links. Shared synthetic suites own independent arithmetic, accuracy modifiers, hit/miss including absorbed hits, rejection, lifetime, atomicity and depleted persistence.

`test_monster_composition_coverage.py::variant_signature` groups ordered effect families, audiences and hit dependencies, excluding identity, element and magnitudes. Both lynx variants join the delivered enemy damage plus enemy hit-rider group. After the goat predecessor, `cliff_stepper` remains its sorted minimum because `trail_hunter` and `wood_stalker` sort later. No representative changes, new composition or missing generic relationship check arise. Run those existing representative and generic/synthetic suites unchanged; keep shards, freeze metadata and existing annotations untouched. The goat's bounded declaration-driven modifier observation remains its predecessor's work. Add no species-specific production smoke or approved-row/magnitude equality tests.

The separate retained `combat-modifier-table` one-test-per-rule contract requires the sole test edit, `test_rule_mane_misdirection_accuracy` in existing `test_combat_modifiers.py::CombatModifierTests`. Follow `test_rule_grain_rattle_accuracy`, using its synthetic `_entity()`, reading the live row from `RULES`, applying the row's `when.buff_active` buff and comparing evaluated output to `rule.then`. This single generic rule-correspondence case uses no species fixture or copied magnitude and creates no new module, shard entry, freeze entry or traceability ID. All other test modules remain unchanged.

## Risks / Trade-offs

The approved prose discloses the ecological boundary. Generic checks establish declaration integrity, not equality to an approval table; editorial review compares authored changes against the literal inventory above. No measured balance claim is made. Reusing a delivered composition needs no new species-specific smoke; all-variant construction and shared mechanism coverage still apply to the new kit. The generic one-test-per-rule obligation still requires a correspondence case for the new modifier, independent of composition reuse.

## Delivery Plan

The content is already approved. A separately authorized apply after the listed predecessor delivers this content unit, display metadata, keyed documentation and the single generic rule-correspondence case. New construction receives the current approved row/kit atomically. Existing individuals keep stored bases, kit, binding and depleted gauges, with no startup reset, live migration or compatibility layer. Rollback reverts the reviewed content unit without recalculating stored gauges. No implementation, sync or archive occurs in this rewrite.

## Historical full-set critique disposition

The original full-batch critique's valid-contact self-guard clarification was fixed in the original crab/hare deltas and common authority; composite/audience citations and approval-record wording were clarified. The current generic self-effect contract retains that boundary after delta removal. The reported band blocker was rejected from the then-read `monster_species.py:666–728`, which already carried hare HP30/55 at low and lynx HP115/165 at mid. Historical Previous HP values were not shipped profiles. No band exceptions, other-species retuning or gameplay reruns were needed. This preserves the original disposition without claiming a new runtime check.

## Rewrite whole-set critique disposition (2026-10-11)

Adopted all three blocking findings. Keyed status now uses `delivered`; both mandatory status-display rows are included; the retained one-test-per-rule contract adds one generic correspondence case and its shared-file conflict, replacing the earlier claim of no test edits. No species-specific battery or representative edit is needed. The no-spec-delta decision and approved literal inventory were upheld. The nonblocking freeze-reason finding concerns only the hare/goat representative edits, whose reason text stays verbatim. Empty untracked spec directories require no stub or artifact and are left alone. This is the single final independent critique of the three rewritten proposals, with corrections recorded here and no runtime acceptance claim.
