# Remaining First-Batch Monster Resource Skills

**Date:** 2026-10-10
**Status:** Approved by the user on 2026-10-10 for the whole five-change batch; the approval record is §12. Approval covers the literals and prose below, not implementation status: only `sway-whistle-sparrow-resource-skill` is delivered first, and the remaining four species stay unimplemented until their own changes land.
**Scope:** Five existing species and their ten existing non-crocodile variants. The approved 2026-10-09 shared-mechanism and crocodile sections remain unchanged.

## 1. Authority and approval boundary

The user requested 「把剩餘現有的其他魔物也完成設計，考量到他們現在的描述，為他們設計符合他們的技能」 and authorized 「現有的風味文字描述可適當修改以方便實作」. This proposed extension replaces the five-species deferral in `2026-10-09-monster-resource-skills-design.md` §1/§7 only as each species is approved and implemented. It does not retrospectively label proposed literals approved. Written-spec approval and explicit approval of the values below precede apply.

The shared identity and hit-dependency contracts, separate monster slice, frozen variant kits, atomic construction and first-owned combat path have landed in the three archived 2026-10-09 changes. No new mechanism prerequisite is needed for this design. No creature-specific resolver branch is permitted.

## 2. Observed implementation and environment decision

`world/lore/monster_species.py` declares all ten target variants with zero MP/SP and magic power, and pins literal physical axes. `_check_profile_bands` checks each physical axis and magic power independently; its docstring explicitly excludes MP/SP. `world/lore/monsters.py` authors `(0, 0)` magic power at every tier; `world/lore/tests/test_monster_species_band_invariant.py` exercises the independent magic-band constraint with synthetic faces. Every proposed damage effect therefore reads `atk_phys`; elemental identity is taxonomy, never a magic-power scalar. The parsed damage element does not scale settlement, as stated in `skill-effect-model`'s elementless-damage contract.

`world/skills/registry/data_monster_abilities.py` contains only the crocodile declaration, already included by `assembly.py`. `SkillEligibility` uses immutable actor-kind/species tuples. `effects/policies.py` supplies occurrence-indexed `requires_hit_from`. `monster_individual.py` validates and persists ordered active/passive kits and a behavior reference. `monster_behaviour.py` considers eligible, affordable active damage skills and first-owned order. These contact composites stay inside that shape without utility planning.

Environmental conditioning is prose-only. No skill in this extension evaluates fog, loose stone, soil, grain or existing light. Its contact action is independently executable; the ecological abilities retain their conditions in narrative. There is no numeric fog advantage, falling-rock rider or light-source amplification. This is a deliberate representational limit, disclosed in player-facing prose below, rather than an environment engine deferred inside these changes.

Evidence for this choice is `world/skills/cast_conditions.py`, whose subjects are ACTOR/EACH_TARGET and whose closed fields cover sexual state plus buff/ownership/equipment predicates, with no room subject or weather facts. `typeclasses/rooms.py` defines scene archetype and anchor identities; `world/maps/wilderness_provider.py` projects coordinates to regional keys and flavor descriptions. Those are not measured fog, light or loose-stone conditions. `buffs.yaml` ground/positional markers are entity buff facts; `test_terrain_marker.py` defines standing-on-it by holding the ground-marker buff. Neither a regional name nor a prose description is evidence of local fog or contacted loose stone.

Existing mounts show timed defense and accuracy in `combat_modifiers.yaml`; `buffs.yaml` also supports ground hazards, positional displacement, round-order and tick DoT. Those stronger controls are unnecessary and deliberately unused. New buff keys are authored content using existing `buff_apply`/`self_buff_apply`, not new effect kinds. A future mechanically conditional proposal would need its own species-agnostic precondition contract; it is outside this batch.

Settled value (user ruling, 2026-10-10): `data_monster_abilities.py:32` sets crocodile `usable_out_of_combat=True`, and that `True` is the correct value, not a mismatch. Under the shared `skill-registry` policy (`openspec/specs/skill-registry/spec.md`, "Every skill declares `usable_out_of_combat` deliberately"), every damage-carrying ability is selectable outside combat, so this extension's new declarations use `True` as well. `combat-only` describes the ability's action shape and targeting — an in-combat contact ability, the same wording the delivered `monster-resource-abilities` main spec uses for the crocodile — and is not a statement about the selection flag. Both delivered crocodile rows, bite costs/effects, profile and kit remain unchanged.

## 3. Shared declaration and acceptance contract

Every new ability is `SkillKind.ACTIVE`, `TargetSpec.SINGLE`, `usable_out_of_combat=True` (the shared `skill-registry` policy: every damage-carrying ability declares `True`; `combat-only`, where this batch uses it, describes the ability's action shape and targeting, not this flag), explicit `FactionConstraint.ANY`, `SkillCategory.ELEMENTAL_MAGIC`, group equal to its element key, `prerequisites=()` and `cast_conditions=()`. Eligibility is `SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=(<species key>,))`; no races, subraces or required capabilities. No passive or progression chain exists.

Effect occurrence 0 is one `damage:<element>:physical` strike. Its policy is `EffectPolicy(coefficient=<authored coefficient>, audience=EffectAudience.ENEMIES)` with no extra strikes, defense bypass, conditional multiplier, state magnitude, transfer or dependency. Targeting remains ordinary physical close contact, living-target and positional-displacement rules. Allies remain selectable under ANY but enemy damage/riders do not affect them.

For target debuffs, occurrence 1 is `buff_apply:<buff key>` with `EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0)`. A hit with fully absorbed damage qualifies; a miss applies no target buff. For defensive composites, occurrence 1 is `self_buff_apply:<buff key>` with `EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF, requires_hit_from=None)`. The self guard is part of an affordable resolved attempt with a valid selected contact target, including a miss; a targeting-rejected or otherwise rejected action applies nothing. No-target requests retain the ordinary SINGLE target gate and do not become self-casts. A self guard cannot depend on enemy hit outcomes because shared audience intersection would exclude the caster. `world/rules/action/routing.py:171-188,232-239` supplies the audience binding and hit intersection; `world/skills/registry/vocab.py` validates actor-bound effect audiences. The SINGLE/ANY damage-plus-self-buff precedent is `world/skills/registry/data_martial_sword.py:182-203`.

All new buff rows have the literal duration below in world seconds, `stacking: refresh`, `tick_interval` absent, no marker, no round_order and `modifiers: {}`. Target rows have `polarity: debuff`; self rows have `polarity: buff`. Each corresponding combat-modifier row uses `when: {buff_active: <key>}` and `then: {<stat>: <delta>}`. Reapplication refreshes duration without accumulating duplicate same-key bonuses/penalties. Expiry or canonical removal eliminates the modifier. The self guards protect only their caster, without blocking a room or protecting an ally.

Nominal costs use the existing resource modifier and action transaction. Affordability precedes dice; resolved hit/miss pays both resources once after effects; failure restores HP, MP/SP, buffs and practice claims. No gauge transfer, recovery, permanent stat change, state reaction or new cost band is authored. Every MP price is 10, retaining the existing single-target apprentice cost classification; composites remain freeform-ineligible under the existing damage-plus-buff shape. MP-related maxima are the literal MP pool below; regeneration and other MP modifiers remain unchanged.

Stored active kit is the single ability key, passive kit empty. `owned_keys()` order is special ability, innate `basic_attack`, innate `flee`; flee remains its independent priority branch. The low-tier species reuse `instinctive` (first_owned, lowest_hp, area preference false, flee 0.35). The two mid-tier species reuse `ambush_predator` (first_owned, lowest_hp, area preference false, flee 0.20). No YAML archetype or tier default changes. Exhaustion of either resource selects basic attack; final resolver gates remain authoritative after initiative changes state.

New construction takes the approved complete row literally and persists identity, kit and profile atomically. Reload retains depleted gauges. No startup reset, automatic live migration or compatibility layer is introduced. Hunt selectors retain all species/variant keys and grades. Player catalogs and lineage exclude these monster-only isolated roots via existing identity filtering; no command syntax/availability changes or command-doc updates are planned.

## 4. 穗鳴雀 (`sway_whistle_sparrow`)

Proposed authored key `grain_shaking_peck`, player label 震穗啄擊, element/group `wind`. Nominal cost is 10 MP and 2 SP. Effects in order are `damage:wind:physical` and `buff_apply:grain_rattle`. Damage coefficient is 0.8; the second policy follows the ENEMIES, requires_hit_from=0 contract in §3. No GaugeTransferPolicy is used.

Buff `grain_rattle` lasts 10 world seconds and mounts `accuracy: -3` through modifier row `grain_rattle_accuracy`. Both variants bind `behaviour_profile_key="instinctive"` and sole active key `grain_shaking_peck`.

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `grain_pecker` | 30 | 20 | 8 | 4 | 7 | 3 | 0 | F |
| `flock_leader` | 55 | 30 | 12 | 8 | 10 | 4 | 0 | E |

These are proposed complete literal rows; only MP/SP change from the existing approval. No value is inferred or recalibrated.

### Published prose and author-note changes

保留「濕穀與牢固的未熟穗不易受影響。」及風暴限制，追加「近身時，牠會配合短促氣流啄擊，命中後使對手短暫分心；此招不需要穀物，也不產生強風或擊退。」

`docs/lore/bestiary.md` and `world/lore/monster_species.py::published_ecology_zh` receive the same proposed sentence edits. In this species' private explanation, replace 「不授予任何可執行技能」 with 「以近身啄擊與短暫命中干擾呈現微弱氣流，震穀生態仍不改造戰場」; hidden origin and unverified conjecture remain untouched. The reason is to describe an independently executable contact action without falsely promising an environmental resolver. The ecological paragraph, habitat and variant direction remain unchanged.

### Species-specific acceptance

Construct both variants through production construction, execute resolver-backed sessions and observe physical HP loss, nominal resource deductions and the authored modifier. A miss skips the target debuff; an absorbed hit still applies it once. Refresh and expiry must preserve the literal magnitude. Reject ineligible owners and insufficient MP/SP before dice or effects. Exhaust each resource independently and resolve basic_attack next. Exercise inclusive flee threshold 0.35, positional-target rejection, late rollback and depleted persistence reload. No scene description or environment-looking request context changes the result.

## 5. 潮燈蟹 (`tide_lamp_crab`)

Proposed authored key `lamp_carapace_claw`, player label 燈甲螯擊, element/group `light`. Nominal cost is 10 MP and 3 SP. Effects in order are `damage:light:physical` and `self_buff_apply:lamp_carapace_guard`. Damage coefficient is 1.0; the second policy follows the SELF, no hit dependency contract in §3. No GaugeTransferPolicy is used.

Buff `lamp_carapace_guard` lasts 20 world seconds and mounts `defense: 2` through modifier row `lamp_carapace_guard_defense`. Both variants bind `behaviour_profile_key="instinctive"` and sole active key `lamp_carapace_claw`.

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `shore_walker` | 30 | 20 | 9 | 5 | 4 | 5 | 0 | F |
| `reef_warden` | 60 | 30 | 15 | 12 | 4 | 7 | 0 | E |

These are proposed complete literal rows; only MP/SP change from the existing approval. No value is inferred or recalibrated.

### Published prose and author-note changes

保留「牠們只能重現已有光源的節奏，不能製造幻覺或偽裝物體。」將「發光不等於治療能力，也不表示牠們掌握光屬性治療術。」改為「牠會在螯擊時收緊甲殼，短暫提高自身防禦；這項動作不依賴光源，發光斑紋與螯擊皆無治療效果，也不屬於光屬性治療術。」

`docs/lore/bestiary.md` and `world/lore/monster_species.py::published_ecology_zh` receive the same proposed sentence edits. In this species' private explanation, replace 「以既有光源為條件的辨識干擾，刻意排除幻覺與治療語意」 with 「追光生態保留既有光源條件；戰鬥採螯擊與甲殼防護，排除幻覺與治療」; hidden origin and unverified conjecture remain untouched. The reason is to describe an independently executable contact action without falsely promising an environmental resolver. The ecological paragraph, habitat and variant direction remain unchanged.

### Species-specific acceptance

Construct both variants through production construction, execute resolver-backed sessions and observe physical HP loss, nominal resource deductions and the authored modifier. A miss still grants the caster defense, without target buff delivery. Refresh and expiry must preserve the literal magnitude. Reject ineligible owners and insufficient MP/SP before dice or effects. Exhaust each resource independently and resolve basic_attack next. Exercise inclusive flee threshold 0.35, positional-target rejection, late rollback and depleted persistence reload. No scene description or environment-looking request context changes the result.

## 6. 築埂兔 (`ridge_burrow_hare`)

Proposed authored key `ridge_bracing_kick`, player label 固埂蹬擊, element/group `earth`. Nominal cost is 10 MP and 3 SP. Effects in order are `damage:earth:physical` and `self_buff_apply:ridge_brace`. Damage coefficient is 0.8; the second policy follows the SELF, no hit dependency contract in §3. No GaugeTransferPolicy is used.

Buff `ridge_brace` lasts 20 world seconds and mounts `defense: 3` through modifier row `ridge_brace_defense`. Both variants bind `behaviour_profile_key="instinctive"` and sole active key `ridge_bracing_kick`.

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `burrow_maker` | 30 | 20 | 9 | 4 | 8 | 3 | 0 | F |
| `nest_guard` | 55 | 30 | 15 | 11 | 6 | 6 | 0 | E |

These are proposed complete literal rows; only MP/SP change from the existing approval. No value is inferred or recalibrated.

### Published prose and author-note changes

保留「牠們只能處理巢穴周圍的鬆土，無法鑽穿岩盤、城牆或石造基礎。」及正常洞道逃離限制，追加「受逼近時，牠會以土屬性力量穩住身體後蹬擊，短暫提高自身防禦；此招不需要挖洞，也不封鎖他人的移動或行動。」

`docs/lore/bestiary.md` and `world/lore/monster_species.py::published_ecology_zh` receive the same proposed sentence edits. In this species' private explanation, replace 「不附帶任何戰鬥或控場能力。」 with 「戰鬥以蹬擊與自身防禦呈現，不附帶定身、封路或瞬間移動。」; hidden origin and unverified conjecture remain untouched. The reason is to describe an independently executable contact action without falsely promising an environmental resolver. The ecological paragraph, habitat and variant direction remain unchanged.

### Species-specific acceptance

Construct both variants through production construction, execute resolver-backed sessions and observe physical HP loss, nominal resource deductions and the authored modifier. A miss still grants the caster defense, without target buff delivery. Refresh and expiry must preserve the literal magnitude. Reject ineligible owners and insufficient MP/SP before dice or effects. Exhaust each resource independently and resolve basic_attack next. Exercise inclusive flee threshold 0.35, positional-target rejection, late rollback and depleted persistence reload. No scene description or environment-looking request context changes the result.

## 7. 岩響山羊 (`rock_echo_goat`)

Proposed authored key `rock_echo_ram`, player label 岩響角撞, element/group `earth`. Nominal cost is 10 MP and 5 SP. Effects in order are `damage:earth:physical` and `buff_apply:rock_echo_stagger`. Damage coefficient is 1.2; the second policy follows the ENEMIES, requires_hit_from=0 contract in §3. No GaugeTransferPolicy is used.

Buff `rock_echo_stagger` lasts 15 world seconds and mounts `agility_flat: -3` through modifier row `rock_echo_stagger_agility_flat`. Both variants bind `behaviour_profile_key="ambush_predator"` and sole active key `rock_echo_ram`.

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `cliff_stepper` | 130 | 30 | 20 | 20 | 16 | 12 | 0 | D |
| `pass_warden` | 170 | 50 | 30 | 26 | 14 | 14 | 0 | C |

These are proposed complete literal rows; only MP/SP change from the existing approval. No value is inferred or recalibrated.

### Published prose and author-note changes

保留「脈動無法粉碎完整岩盤，不會造成大範圍地震。」將「地形與既有鬆石是能力成立的重要條件，不能將牠們描述為隨處都能引發同等規模的崩塌。」改為「落石脈動需要接觸岩面及既有鬆石；近身角撞則能在沒有鬆石時使用，命中後使對手短暫步伐不穩，不附帶落石傷害或崩塌。」

`docs/lore/bestiary.md` and `world/lore/monster_species.py::published_ecology_zh` receive the same proposed sentence edits. In this species' private explanation, replace 「威力取決於既有鬆石」 with 「落石生態取決於既有鬆石，戰鬥角撞與短暫步伐干擾無環境條件」; hidden origin and unverified conjecture remain untouched. The reason is to describe an independently executable contact action without falsely promising an environmental resolver. The ecological paragraph, habitat and variant direction remain unchanged.

### Species-specific acceptance

Construct both variants through production construction, execute resolver-backed sessions and observe physical HP loss, nominal resource deductions and the authored modifier. A miss skips the target debuff; an absorbed hit still applies it once. Refresh and expiry must preserve the literal magnitude. Reject ineligible owners and insufficient MP/SP before dice or effects. Exhaust each resource independently and resolve basic_attack next. Exercise inclusive flee threshold 0.20, positional-target rejection, late rollback and depleted persistence reload. No scene description or environment-looking request context changes the result.

## 8. 霧鬃山貓 (`fog_mane_lynx`)

Proposed authored key `mane_crosswind_pounce`, player label 鬃風佯撲, element/group `wind`. Nominal cost is 10 MP and 5 SP. Effects in order are `damage:wind:physical` and `buff_apply:mane_misdirection`. Damage coefficient is 1.0; the second policy follows the ENEMIES, requires_hit_from=0 contract in §3. No GaugeTransferPolicy is used.

Buff `mane_misdirection` lasts 15 world seconds and mounts `accuracy: -5` through modifier row `mane_misdirection_accuracy`. Both variants bind `behaviour_profile_key="ambush_predator"` and sole active key `mane_crosswind_pounce`.

| Variant | HP | MP | SP | atk_phys | agility | defense | magic_power | Grade |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `wood_stalker` | 115 | 30 | 20 | 20 | 20 | 10 | 0 | D |
| `trail_hunter` | 165 | 50 | 30 | 25 | 22 | 12 | 0 | C |

These are proposed complete literal rows; only MP/SP change from the existing approval. No value is inferred or recalibrated.

### Published prose and author-note changes

將「能力依賴既有霧氣，乾燥、無霧的環境中優勢大幅減弱。」改為「聚霧依賴既有霧氣，乾燥、無霧的環境中聚霧優勢大幅減弱；近身時的鬃風佯撲仍可使用，命中後使對手短暫誤判動作，戰鬥不另計霧氣加成。」保留「牠仍有足跡、氣味與聲音，不能完全隱形、製造任意幻覺或瞬間移動。」

`docs/lore/bestiary.md` and `world/lore/monster_species.py::published_ecology_zh` receive the same proposed sentence edits. In this species' private explanation, replace 「以環境條件（霧氣）限定優勢」 with 「以霧氣限定聚霧生態；近身佯撲及短暫命中干擾由鬃毛氣流與動作產生」; hidden origin and unverified conjecture remain untouched. The reason is to describe an independently executable contact action without falsely promising an environmental resolver. The ecological paragraph, habitat and variant direction remain unchanged.

### Species-specific acceptance

Construct both variants through production construction, execute resolver-backed sessions and observe physical HP loss, nominal resource deductions and the authored modifier. A miss skips the target debuff; an absorbed hit still applies it once. Refresh and expiry must preserve the literal magnitude. Reject ineligible owners and insufficient MP/SP before dice or effects. Exhaust each resource independently and resolve basic_attack next. Exercise inclusive flee threshold 0.20, positional-target rejection, late rollback and depleted persistence reload. No scene description or environment-looking request context changes the result.

## 9. Dependency and conflict matrix

| Order | Change | Required predecessor | Standalone outcome |
|---|---|---|---|
| 1 | `sway-whistle-sparrow-resource-skill` | Archived eligibility + hit dependency + crocodile consumer | Both 穗鳴雀 variants executable |
| 2 | `tide-lamp-crab-resource-skill` | `sway-whistle-sparrow-resource-skill` | Both 潮燈蟹 variants executable |
| 3 | `ridge-burrow-hare-resource-skill` | `tide-lamp-crab-resource-skill` | Both 築埂兔 variants executable |
| 4 | `rock-echo-goat-resource-skill` | `ridge-burrow-hare-resource-skill` | Both 岩響山羊 variants executable |
| 5 | `fog-mane-lynx-resource-skill` | `rock-echo-goat-resource-skill` | Both 霧鬃山貓 variants executable |

The serial predecessor is required for cumulative main-spec replacements, even though all five ability definitions reuse the same landed APIs. Approval may review the set together; implementation remains per-change and no change exceeds the one-day sizing in its proposal.

| Pair | Dependency | Code/main-spec conflict |
|---|---|---|
| `sway-whistle-sparrow-resource-skill` / `tide-lamp-crab-resource-skill` | Later depends directly on earlier | All common surfaces below; serialize |
| `sway-whistle-sparrow-resource-skill` / `ridge-burrow-hare-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `sway-whistle-sparrow-resource-skill` / `rock-echo-goat-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `sway-whistle-sparrow-resource-skill` / `fog-mane-lynx-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `tide-lamp-crab-resource-skill` / `ridge-burrow-hare-resource-skill` | Later depends directly on earlier | All common surfaces below; serialize |
| `tide-lamp-crab-resource-skill` / `rock-echo-goat-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `tide-lamp-crab-resource-skill` / `fog-mane-lynx-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `ridge-burrow-hare-resource-skill` / `rock-echo-goat-resource-skill` | Later depends directly on earlier | All common surfaces below; serialize |
| `ridge-burrow-hare-resource-skill` / `fog-mane-lynx-resource-skill` | Later depends transitively on earlier | All common surfaces below; serialize |
| `rock-echo-goat-resource-skill` / `fog-mane-lynx-resource-skill` | Later depends directly on earlier | All common surfaces below; serialize |

Shared-file serialization points are `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`, `docs/lore/bestiary.md`, `docs/lore/monster-creation-guidelines.md`, `docs/development/adding-spells.md`. Every pair also overlaps the full registry replacement blocks and the crocodile ecology requirement in `openspec/specs/monster-resource-abilities/spec.md`. `world/skills/registry/assembly.py` remains unchanged but is an ordered assembly review boundary; `monster_behaviour.yaml` remains unchanged because existing archetypes suffice. No new player command documentation conflict is introduced.

## 10. Contract cutover, documentation and verification

Each change includes complete MODIFIED blocks for Numeric combat profiles, Special abilities and approved first-batch profiles in `monster-species-registry`, preserving original requirement/scenario match keys and unaffected scenarios. Approved cumulative pool rows replace the stale crocodile-only zero-pool exception. The deferral applies only to not-yet-delivered species; the final lynx change leaves no first-batch species deferred. The crocodile ecology requirement's trailing five-species deferral is narrowed on each step without changing crocodile mechanics. All profile/grade and pool approval gates remain explicit.

The first species revises the stale module claim that all six abilities have no executable form; each successor updates the actual delivered/deferred list. Final wording must describe six configured species rather than claiming six ecological processes have environment simulations. Existing bestiary historical approval appendices stay historical, with a current implementation-status addition scoped to delivered species; update current boundary prose and author guides without rewriting the approved 2026-10-09 authority. Adding-spells documents the five compositions as consumers of existing vocabulary. No test or document may label pending values user-approved before approval.

Each implementation extends existing monster profile/kit and policy tests plus one species data-contract production smoke registered exactly in rules-b (index 2), matching the crocodile precedent. Its shipped assertions are registered in `tools/test_data_freeze.json`; synthetic fixtures cover general mechanics separately. Acceptance requires formal construction for both variants, actual provider/resolver actions, hit/miss, exact cost, both exhaustion axes/fallback, refresh/expiry, absorbed-hit riders, rollback and reload. Use a controlled valid opponent, isolate clock recovery for nominal deltas and keep ordinary recovery unchanged. No live generative or image service is used. Existing hunts must still match unchanged identity selectors; crocodile rows/cost/effects/kit/profile remain pinned.

Per change run focused affected Evennia labels using the approved test environment, data/observability checks as applicable, `uv run --locked python -m tools.contract_gate`, and strict OpenSpec validation. These are implementation acceptance tasks, not evidence already obtained by this planning document. Planning validation records and critique results are reported separately.

## 11. Exact approval list

Approve the shared prose-only environmental choice in §2; the declarations, targeting/audience/hit semantics, cost order and kit order in §3; and every ability key/label, element, coefficient, MP/SP price, buff key/duration/polarity/modifier, complete literal row, existing behavior-profile binding and quoted prose/author-note replacement in §§4–8. Approval of this batch amends the cited main-spec sentences so each cumulative “Approved delivered resource rows are literal” table becomes the pool approval record; the historical physical-axis table is not an MP/SP record. Existing physical axes and grades are retained, not newly calibrated. No separate MP scaling, resource reaction, recovery share or environment bonus is requested.

## 12. 核准紀錄（2026-10-10）

本節於使用者核准後追加，不修改上文任何已核准範圍與文字；上文各節的 “proposed / pending user
approval” 敘述自本節起由下方紀錄取代，但文字本身不對應改寫（沿用
`2026-10-05-monster-data-model-design.md`「平衡核准落地」的追加慣例）。

使用者於 2026-10-10 在工作對話中，核准本文件 §11 所列的完整內容，範圍為下列五個變更，依 §9 的
序列依序落地：

1. `sway-whistle-sparrow-resource-skill`（§4，穗鳴雀）
2. `tide-lamp-crab-resource-skill`（§5，潮燈蟹）
3. `ridge-burrow-hare-resource-skill`（§6，築埂兔）
4. `rock-echo-goat-resource-skill`（§7，岩響山羊）
5. `fog-mane-lynx-resource-skill`（§8，霧鬃山貓）

核准項目逐項對應 §11：§2 的共用「僅以文字描述環境條件」決策；§3 的宣告形狀、目標／受眾／
命中相依語意、付費順序與套組順序；以及 §4–§8 各物種的技能鍵／標籤、元素、係數、MP/SP 價格、
buff 鍵／持續時間／極性／修正值、完整數值列、既有行為設定檔綁定，與所有引號內的公布文字及
作者註記替換。

落地狀態（本節不宣告尚未落地的部分）：本批次的第一個落地變更為
`sway-whistle-sparrow-resource-skill`；其餘四個物種的數值列與技能雖已核准，仍維持既有的零 MP/SP
池與敘事邊界，須由各自的變更落地後才具可執行形式。核准不改變既有狩獵委託的物種／變體選擇器、
個體危險評級，也不使任何未交付物種取得可執行能力。
