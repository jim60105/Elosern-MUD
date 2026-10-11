# Design

## Context

See proposal.md for the mandate and approval history. Authority `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §6 owns this species' literals; §§2–3 define the shared contact contract, approved with the whole batch on 2026-10-10 in §12. Implementation remains pending. The generalization cutover at `8f33f414` makes profile obligations, kit delivery and identity authored registry data. Existing declaration, construction and policy APIs need no extension.

## Goals / Non-Goals

Deliver one complete ability and both variants using existing effects, buff modifiers and construction/policy APIs. Exclude environment inference, new effect kinds, utility selection, player surface changes and other species data edits. Consume the generic contracts without modifying specs or restoring species-specific scenarios.

## Decisions

### Approved declaration and ordered execution

Append `ridge_bracing_kick`, label 固埂蹬擊, to the existing monster ROWS after delivered content. Preserve existing order/content. Declare `SkillKind.ACTIVE`, `TargetSpec.SINGLE`, `usable_out_of_combat=True`, explicit `FactionConstraint.ANY`, element/group `earth` and `SkillCategory.ELEMENTAL_MAGIC`. The historical “combat-only” phrase describes contact action/targeting, with selection outside combat retaining the ordinary battlefield gate. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("ridge_burrow_hare",))`; no race/subrace restrictions or required capabilities. `prerequisites=()` and `cast_conditions=()`; no passive or progression chain exists.

Ordered effects are `damage:earth:physical` and `self_buff_apply:ridge_brace`. Occurrence 0 uses `EffectPolicy(coefficient=0.8, audience=EffectAudience.ENEMIES)` and no hit dependency. Occurrence 1 uses `EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF, requires_hit_from=None)`. All remaining fields retain existing defaults. No GaugeTransferPolicy, state magnitude, bypass, extra strike or environment predicate is used. Costs are `{"mp": 10, "sp": 3}`. Damage reads `atk_phys`; element is taxonomy and adds no magic-power scaling. Ordinary living/contact/positional target gates apply. ANY permits ally selection, while enemy damage never reaches an ally.

Affordability for both adjusted resources precedes dice/effects. A resolved hit or miss pays both costs once after effects; rejected actions write nothing and late failure restores gauges, buffs and practice claims. Existing resource modifiers, reactions and recovery remain unchanged. MP 10 retains the apprentice single-target cost classification; the composite remains freeform-ineligible.

### Approved timed modifier

Add `ridge_brace` with duration 20 world seconds, `stacking: refresh`, `polarity: buff`, `modifiers: {}` and no tick interval, marker or round_order. Modifier row `ridge_brace_defense` has `when: {buff_active: ridge_brace}` and `then: {defense: 3}`. A valid affordable resolved contact attempt grants only the caster guard, including a miss. Rejected or no-target requests grant nothing and do not become self-casts. A source-enemy-hit dependency would exclude the caster through shared audience intersection; retain `requires_hit_from=None`. Refresh changes expiry without accumulating magnitude; expiry/canonical removal eliminates the modifier. No ally protection, action lock, DoT, ground hazard or displacement is introduced. The historical SINGLE/ANY composite precedent is `data_martial_sword.py::true_sword_saint`.

`status_display.py` rejects missing buff/rule display codes at import. Add both codes to `world/rules/rulebook/status_display.yaml`, following the delivered guard precedent, with severity `beneficial`. Use labels 固埂蹬擊 and 固埂蹬擊防禦提升 for the buff and modifier respectively. These presentation labels derive from the approved ability/effect; they introduce no mechanic or change to the approved skill label.

### Approved complete rows and policy binding

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `burrow_maker` | 30 | 20 | 9 | 4 | 8 | 3 | 0 | F |
| `nest_guard` | 55 | 30 | 15 | 11 | 6 | 6 | 0 | E |

Only MP/SP change. Preserve `profile_required=True`, species key `ridge_burrow_hare`, variant keys, tier/default/ordinary membership, physical axes and grades. Both variants declare `active_skill_keys=("ridge_bracing_kick",)`, `passive_skill_keys=()` and `behaviour_profile_key="instinctive"`. Owned order is special ability, innate `basic_attack`, innate `flee`; flee retains independent priority. Existing profile is `first_owned`, `lowest_hp`, area preference false, inclusive flee threshold 0.35. Behavior YAML stays unchanged. Exhaustion of either resource selects ordinary attack; final resolver gates remain authoritative after initiative changes state.

### Approved public/private prose and keyed status

Retain 「牠們只能處理巢穴周圍的鬆土，無法鑽穿岩盤、城牆或石造基礎。」 and the normal-tunnel escape limit. Append 「受逼近時，牠會以土屬性力量穩住身體後蹬擊，短暫提高自身防禦；此招不需要挖洞，也不封鎖他人的移動或行動。」 to `published_ecology_zh` and the current bestiary ability boundary.

In `author_explanation_zh`, replace 「不附帶任何戰鬥或控場能力。」 with 「戰鬥以蹬擊與自身防禦呈現，不附帶定身、封路或瞬間移動。」. Retain hidden origin, unverified conjecture, habitat, ecological paragraph and variant direction. The independent contact action needs no measured soil or digging fact; narrative and forged request context grant no effect.

Change the species and both variant statuses in this species' current keyed `bestiary` block from `narrative` to `delivered`, the checker's actual kit-backed status value, preserving keys, default/parent relationships and public-field links. Update current delivery notes for this species only. Historical approval appendices and the 2026-10-09/10 authorities remain unchanged. Existing author guides already describe generic content authoring; no guide edits or global species list are needed.

### Existing contracts and bounded test work

No spec delta is needed. This change declares `skip_specs: true` and removes the old four capability deltas without replacement stubs. Current contracts cover complete declared profiles, validated kit references, shared effect/payment semantics, atomic construction, live-state preservation and keyed bestiary coverage. The archived cutover's `retained-contracts.md`, `cutover-matrix.md` and `wp7-integrated-acceptance.md` explain the retired approval tables/species scenarios and retained bounds/mechanisms.

`test_monster_species_content.py::ShippedProfileConstructionTests` constructs and reloads every live variant. `AuthoredMonsterKitContractTests` in `test_registry_contract.py` derives all kit references and checks kind, identity, cost/effect and hit/audience closure. `test_bestiary_documentation.py` checks keyed coverage/status and public links. Shared synthetic suites own independent arithmetic, hit/miss, rejection, lifetime, atomicity and depleted persistence.

`test_monster_composition_coverage.py::variant_signature` groups ordered effect families, audiences and hit dependencies, excluding identity, element and magnitudes. This ability joins the delivered enemy damage plus hit-independent self-guard group. Its sorted minimum changes from `reef_warden` to `burrow_maker`. Change only `REPRESENTATIVE_VARIANT` in existing `test_tide_lamp_crab_resource_skill.py`; skill, buff, costs, duration and binding are already declaration-derived and its defense observation fits both guards. Retain the real policy/resolver, caster-only miss guard, refresh/expiry, payment, fallback, flee and committed reload observations. Keep existing module/class registration and annotations; no new test file, literal approval assertions, shard entry or freeze entry. The species name in the filename is historical; the representative declaration determines coverage.

The retained `combat-modifier-table` one-test-per-rule contract separately requires `test_rule_ridge_brace_defense` in existing `test_combat_modifiers.py::CombatModifierTests`. Follow `test_rule_lamp_carapace_guard_defense`, using its synthetic `_entity()`, reading the live row from `RULES`, applying the row's `when.buff_active` buff and comparing evaluated output to `rule.then`. This single rule-correspondence case has no copied magnitude or species fixture and needs no new ledger/shard entry. The rebound smoke's first-line data-contract reason and freeze reason remain verbatim for seed/ledger agreement.

## Risks / Trade-offs

The approved prose discloses the ecological boundary. Generic checks establish declaration integrity, not equality to an approval table; editorial review compares authored changes against the literal inventory above. No measured balance claim is made. Although this composition is reused, the existing coverage contract requires the representative-key rebind.

## Delivery Plan

The content is already approved. A separately authorized apply after the listed predecessor delivers this content unit, display metadata, keyed documentation and bounded representative/rule-correspondence edits. New construction receives the current approved row/kit atomically. Existing individuals keep stored bases, kit, binding and depleted gauges, with no startup reset, live migration or compatibility layer. Rollback reverts the reviewed content unit without recalculating stored gauges. No implementation, sync or archive occurs in this rewrite.

## Historical full-set critique disposition

The original full-batch critique adopted the self-guard target-boundary finding. Only affordable resolved casts with a valid selected contact target grant guard, including misses; rejected/no-target requests grant nothing. The original delta added a rejection scenario; that boundary now lives generically in “Timed monster effects follow declared recipients and lifetime”. The SINGLE/ANY composite and audience-intersection rationale remains above.

The original critique's pre-cutover band blocker was rejected from the then-read `monster_species.py:666–728`, which already carried hare HP30/55 at low and lynx HP115/165 at mid. The reviewer used the historical Previous HP column and wrong cat tiers. No gameplay checks were rerun to confirm it and no band exception was proposed. Approval-record clarification was recorded in authority §11. This preserves the original review disposition without claiming a new runtime check.

## Rewrite whole-set critique disposition (2026-10-11)

Adopted all three blocking findings. Keyed status now uses `delivered`; both mandatory status-display rows are included; the retained one-test-per-rule contract adds one generic correspondence case and its shared-file conflict. The no-spec-delta decision and approved literal inventory were upheld. Adopted the nonblocking instruction to preserve smoke data-contract/freeze reason text verbatim. The empty untracked spec directories are harmless filesystem remnants of deleted deltas, require no stub or artifact, and are left alone. This is the single final independent critique of the three rewritten proposals, with corrections recorded here and no runtime acceptance claim.
