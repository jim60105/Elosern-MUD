# Design

## Context

See proposal.md for the mandate and approval history. Authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §7 owns this species' literals; §§2–3 define the shared contact contract, approved with the whole batch on 2026-10-10 in §12. Implementation remains pending. The generalization cutover at `8f33f414` makes profile obligations, kit delivery and identity authored registry data. Existing declaration, construction and policy APIs need no extension.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and other species data edits. Consume the generic contracts without modifying specs or restoring species-specific scenarios.

## Decisions

### Approved declaration and ordered execution

Append `rock_echo_ram`, label 岩響角撞, to the existing monster ROWS after delivered content. Preserve existing order/content. Declare `SkillKind.ACTIVE`, `TargetSpec.SINGLE`, `usable_out_of_combat=True`, explicit `FactionConstraint.ANY`, element/group `earth` and `SkillCategory.ELEMENTAL_MAGIC`. The historical “combat-only” phrase describes contact action/targeting, with selection outside combat retaining the ordinary battlefield gate. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("rock_echo_goat",))`; no race/subrace restrictions or required capabilities. `prerequisites=()` and `cast_conditions=()`; no passive or progression chain exists.

Ordered effects are `damage:earth:physical` and `buff_apply:rock_echo_stagger`. Occurrence 0 uses `EffectPolicy(coefficient=1.2, audience=EffectAudience.ENEMIES)` and no hit dependency. Occurrence 1 uses `EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0)`. All remaining fields retain existing defaults. No GaugeTransferPolicy, state magnitude, bypass, extra strike or environment predicate is used. Costs are `{"mp": 10, "sp": 5}`. Damage reads `atk_phys`; element is taxonomy and adds no magic-power scaling. Ordinary living/contact/positional target gates apply. ANY permits ally selection, while enemy damage/riders never reach an ally.

Affordability for both adjusted resources precedes dice/effects. A resolved hit or miss pays both costs once after effects; rejected actions write nothing and late failure restores gauges, buffs and practice claims. Existing resource modifiers, reactions and recovery remain unchanged. MP 10 retains the apprentice single-target cost classification; the composite remains freeform-ineligible.

### Approved timed modifier

Add `rock_echo_stagger` with duration 15 world seconds, `stacking: refresh`, `polarity: debuff`, `modifiers: {}` and no tick interval, marker or round_order. Modifier row `rock_echo_stagger_agility_flat` has `when: {buff_active: rock_echo_stagger}` and `then: {agility_flat: -3}`. A miss applies no target buff; a source hit qualifies even when HP damage is fully absorbed. Apply the contribution once to the selected hit enemy, with no caster/ally delivery. Refresh changes expiry without accumulating magnitude; expiry/canonical removal eliminates the modifier. No action lock, DoT, ground hazard or displacement is introduced.

`status_display.py` rejects missing buff/rule display codes at import. Add both codes to `world/rules/rulebook/status_display.yaml`, following the delivered enemy-rider precedent, with severity `harmful`. Use labels 岩響角撞 and 岩響角撞敏捷下降 for the buff and modifier respectively. These presentation labels derive from the approved ability/effect; they introduce no mechanic or change to the approved skill label.

### Approved complete rows and policy binding

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `cliff_stepper` | 130 | 30 | 20 | 20 | 16 | 12 | 0 | D |
| `pass_warden` | 170 | 50 | 30 | 26 | 14 | 14 | 0 | C |

Only MP/SP change. Preserve `profile_required=True`, species key `rock_echo_goat`, variant keys, tier/default/ordinary membership, physical axes and grades. Both variants declare `active_skill_keys=("rock_echo_ram",)`, `passive_skill_keys=()` and `behaviour_profile_key="ambush_predator"`. Owned order is special ability, innate `basic_attack`, innate `flee`; flee retains independent priority. Existing profile is `first_owned`, `lowest_hp`, area preference false, inclusive flee threshold 0.20. Behavior YAML stays unchanged. Exhaustion of either resource selects ordinary attack; final resolver gates remain authoritative after initiative changes state.

### Approved public/private prose and keyed status

Retain 「脈動無法粉碎完整岩盤，不會造成大範圍地震。」. Replace 「地形與既有鬆石是能力成立的重要條件，不能將牠們描述為隨處都能引發同等規模的崩塌。」 with 「落石脈動需要接觸岩面及既有鬆石；近身角撞則能在沒有鬆石時使用，命中後使對手短暫步伐不穩，不附帶落石傷害或崩塌。」 in `published_ecology_zh` and the current bestiary ability boundary.

In `author_explanation_zh`, replace 「威力取決於既有鬆石」 with 「落石生態取決於既有鬆石，戰鬥角撞與短暫步伐干擾無環境條件」. Retain hidden origin, unverified conjecture, habitat, ecological paragraph and variant direction. The independent contact action needs no measured loose-stone fact; narrative and forged request context grant no effect.

Change the species and both variant statuses in this species' current keyed `bestiary` block from `narrative` to `delivered`, the checker's actual kit-backed status value, preserving keys, default/parent relationships and public-field links. Update current delivery notes for this species only. Historical approval appendices and the 2026-10-09/10 authorities remain unchanged. Existing author guides already describe generic content authoring; no guide edits or global species list are needed.

### Existing contracts and bounded test work

No spec delta is needed. This change declares `skip_specs: true` and removes the old four capability deltas without replacement stubs. Current contracts cover complete declared profiles, validated kit references, shared effect/payment semantics, atomic construction, live-state preservation and keyed bestiary coverage. The archived cutover's `retained-contracts.md`, `cutover-matrix.md` and `wp7-integrated-acceptance.md` explain the retired approval tables/species scenarios and retained bounds/mechanisms.

`test_monster_species_content.py::ShippedProfileConstructionTests` constructs and reloads every live variant. `AuthoredMonsterKitContractTests` in `test_registry_contract.py` derives all kit references and checks kind, identity, cost/effect and hit/audience closure. `test_bestiary_documentation.py` checks keyed coverage/status and public links. Shared synthetic suites own independent arithmetic, hit/miss, rejection, lifetime, atomicity and depleted persistence.

`test_monster_composition_coverage.py::variant_signature` groups ordered effect families, audiences and hit dependencies, excluding identity, element and magnitudes. This ability joins the delivered enemy damage plus enemy hit-rider group. Its sorted minimum changes from `flock_leader` to `cliff_stepper`. Rebind `REPRESENTATIVE_VARIANT` in existing `test_sway_whistle_sparrow_resource_skill.py`; keep current module/class registration, real construction/policy/resolver/payment/reload observations and annotations.

The same smoke currently reads `accuracy` for baseline, application, refresh and expiry. Replace those observations with the axis/delta read independently from the live combat-modifier row whose `when.buff_active` names the representative's mounted buff. Assert the row resolves, the declared contribution changes only the intended target, refresh retains one contribution and expiry restores its prior value. Observe `agility_flat` for this representative without copying `-3`, profile values, ability keys or species allowlists into expectations. Costs, duration, identity and binding remain declaration-derived. Shared synthetic fixtures retain fixed arithmetic and accuracy-mechanism coverage. This bounded consumer repair needs no coverage-selector changes, new composition, new test module, shard entry or freeze entry. The species name in the filename is historical; the representative declaration determines coverage.

The retained `combat-modifier-table` one-test-per-rule contract separately requires `test_rule_rock_echo_stagger_agility_flat` in existing `test_combat_modifiers.py::CombatModifierTests`. Follow `test_rule_grain_rattle_accuracy`, using its synthetic `_entity()`, reading the live row from `RULES`, applying the row's `when.buff_active` buff and comparing evaluated output to `rule.then`. This single rule-correspondence case has no copied magnitude or species fixture and needs no new ledger/shard entry. The rebound smoke's first-line data-contract reason and freeze reason remain verbatim for seed/ledger agreement.

## Risks / Trade-offs

The approved prose discloses the ecological boundary. Generic checks establish declaration integrity, not equality to an approval table; editorial review compares authored changes against the literal inventory above. No measured balance claim is made. Rebinding without replacing the accuracy-only observation would leave a false consumer oracle for the agility modifier, so the bounded test task handles both together.

## Delivery Plan

The content is already approved. A separately authorized apply after the listed predecessor delivers this content unit, display metadata, keyed documentation and bounded representative/consumer/rule-correspondence edits. New construction receives the current approved row/kit atomically. Existing individuals keep stored bases, kit, binding and depleted gauges, with no startup reset, live migration or compatibility layer. Rollback reverts the reviewed content unit without recalculating stored gauges. No implementation, sync or archive occurs in this rewrite.

## Historical full-set critique disposition

The original full-batch critique's valid-contact self-guard clarification was fixed in the original crab/hare deltas and common authority; composite/audience citations and approval-record wording were clarified. The current generic self-effect contract retains that boundary after delta removal. The reported band blocker was rejected from the then-read `monster_species.py:666–728`, which already carried hare HP30/55 at low and lynx HP115/165 at mid. Historical Previous HP values were not shipped profiles. No band exceptions, other-species retuning or gameplay reruns were needed. This preserves the original disposition without claiming a new runtime check.

## Rewrite whole-set critique disposition (2026-10-11)

Adopted all three blocking findings. Keyed status now uses `delivered`; both mandatory status-display rows are included; the retained one-test-per-rule contract adds one generic correspondence case and its shared-file conflict. The no-spec-delta decision, representative/consumer-axis reasoning and approved literal inventory were upheld. Adopted the nonblocking instruction to preserve smoke data-contract/freeze reason text verbatim. The empty untracked spec directories are harmless filesystem remnants of deleted deltas, require no stub or artifact, and are left alone. This is the single final independent critique of the three rewritten proposals, with corrections recorded here and no runtime acceptance claim.
