# Design

## Context

See proposal.md (Why). Shared delivery facts are in `mudfilm-slime-species` design D1–D8. Specific facts at `1b1be7b8`:

- `MONSTER_TIER_REGISTRY["high"]`: guild rank range `("B", "A")`, magic band `(0, 0)`.
- Legacy `_legacy_action`: `use_area = (profile.prefer_area_when_multiple_enemies and len(enemies) > 1 and area_skills) or (not single_skills and area_skills)`; `pack_hunter` in `world/rules/rulebook/monster_behaviour.yaml` has `skill_choice: highest_expected_damage`, `prefer_area_when_multiple_enemies: true`, `flee_hp_fraction: 0.20`, `decision_mode: legacy`.
- Area physical precedent: `whirlwind_slash` (`TargetSpec.AREA`, `damage:none:physical`). Fire precedents in `data_fire.py` use `damage:fire:magic`; this kit uses `damage:fire:physical` like the other monster abilities' `damage:<element>:physical`.
- `spell_tier_for` uses the `area_mp` column for `TargetSpec.AREA` and `single_mp` otherwise; MP costs must fall inside a band.
- The tuning fingerprint covers buff definitions, modifier rules, intelligence, mode overrides and bindings of named variants only; this change adds none of these.

## Goals / Non-Goals

**Goals:** one complete high-tier species with two usable fire strikes and keyed documentation.

**Non-Goals:** placement and boss site; burning damage over time, terrain fire, wallow-drying or root-softening mechanics; elemental immunity; any utility activation.

## Decisions

### D1. Species row (append after `sticky_palm_goblin`)

- `key="ember_bristle_boar"`, `display_name_zh="焙鬃野豬"`; published fields: design §4.5's three quoted passages verbatim; `habitat_tags=("western_hills_valleys",)`.
- `author_hidden_truth_zh="（作者私有：隱秘真相）本物種沒有已定的起源真相；鬃毛熱力的成因不在設定中交代。"`
- `author_explanation_zh="（作者私有：作者解釋）高階獨居野豬：以自身魔力維持肩背鬃毛的局部熱力，連結烘乾泥窩與烘軟根莖；戰鬥呈現為身體力量主導的火屬性物理衝撞與橫掃，魔力資質維持高階帶狀值。"`
- `author_conjecture_zh="（作者私有：尚未證實的猜想）燒炭工人相信焙鬃野豬偏愛舊炭窯是為了取暖，這種說法尚未證實。"`
- `default_variant_key="warm_den_boar"`, `ordinary_variant=True`.

### D2. Variant row (append after `reservoir_warden`)

`MonsterVariant("warm_den_boar", "ember_bristle_boar", "焙窩型", "普通版本，反覆使用烘乾的泥窩與固定覓食路線。", "high", True, MonsterCombatProfile(...), "B", True, active_skill_keys=("ember_tusk_charge", "ember_bristle_sweep"), passive_skill_keys=(), behaviour_profile_key="pack_hunter")`. Profile: all axes inside the high band, `magic_power=0`; `mp` and `sp` each no lower than twice the larger of the two skills' costs in that resource; record in the review why the literals express an ordinary B baseline below the A crocodile variant's threat.

### D3. Skill rows

```python
_skill(
    "ember_tusk_charge",
    "熱鬃衝撞",
    "以發熱的肩背鬃毛帶動身體衝撞單一敵方目標，造成火屬性物理傷害。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": <int inside a single_mp band>, "sp": <positive int>},
    usable_out_of_combat=True,
    element="fire",
    effects=["damage:fire:physical"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="fire",
    faction_constraint=FactionConstraint.ANY,
    eligibility=SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("ember_bristle_boar",)),
    prerequisites=(),
    effect_policies=(EffectPolicy(coefficient=<float>, audience=EffectAudience.ENEMIES),),
),
_skill(
    "ember_bristle_sweep",
    "熱鬃橫掃",
    "甩動發熱的粗鬃橫掃周圍所有敵方目標，對每個目標造成火屬性物理傷害。",
    SkillKind.ACTIVE,
    TargetSpec.AREA,
    cost={"mp": <int inside an area_mp band>, "sp": <positive int>},
    usable_out_of_combat=True,
    element="fire",
    effects=["damage:fire:physical"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="fire",
    faction_constraint=FactionConstraint.ANY,
    eligibility=SkillEligibility(allowed_actor_kinds=("monster",), allowed_species=("ember_bristle_boar",)),
    prerequisites=(),
    effect_policies=(EffectPolicy(coefficient=<float, below the charge's>, audience=EffectAudience.ENEMIES),),
),
```

Both skills are shape-eligible for freeform scaling (`world/skills/cost_tiers.py::is_freeform_eligible`: active, elemental, positive `mp`, only `damage` effects), unlike every shipped kit skill, which carries a non-damage effect. Scaling is still unreachable: `world/rules/progression/_scaling.py::freeform_scales_for` returns `()` unless `freeform_mastery_entitled` finds the element's `<element>_mastery` passive lawfully owned, and no monster kit declares a mastery. The shared predicate is not edited; D7 corrects the one kit-contract assertion that over-states this.

### D4. Narration

`data_fire.py`: `NarrationRow("ember_tusk_charge", action=("{actor} 鬃尖透出暗紅光，低頭朝對手直衝而去。", "{actor} 蹬開土屑，帶著熱氣的肩背猛然撞上前。"))` and `NarrationRow("ember_bristle_sweep", action=("{actor} 猛力甩動粗鬃，帶熱的橫掃掠過身旁每個身影。", "{actor} 原地扭身，烘焦的根皮與熱風一起向四周掃開。"))`.

### D5. AI

`pack_hunter` legacy, no rulebook edit. Rationale for the review: aggressive selection by expected damage, area preference against a party, and a flee threshold that lets "either side flee through a legal affordable route" (design §7.3) apply to the boar. `support_kit_mode_violations` stays empty because both actives carry damage.

### D6. Bestiary, ledger, review

- Overview row `| 高階 | 焙鬃野豬 | 西部偏遠岩林與廢棄燒炭地 | 肩背鬃毛的局部熱力烘乾泥窩、烘軟根莖 | 焙窩型 |`.
- New `## 高階魔物` heading after the `## 中階魔物` sections and before `<!-- bestiary-current-end -->`, with `### 焙鬃野豬`, a `bestiary` block (species/parent `ember_bristle_boar`, sole variant `warm_den_boar` `delivered`, six public fields, status `delivered`), affirmative paragraphs **原型與棲地。**, **外觀。**, **生態與在地關係。** (including 「赤背」), **戰鬥中的表現。**, variant row `| 焙窩型 | 普通版本，反覆使用烘乾的泥窩與固定覓食路線 |`.
- Ledger row for `ember_bristle_boar`.
- Review section "焙鬃野豬" in `docs/development/monster-content-expansion.md`.

### D7. Tests

1. `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests.test_every_declared_kit_skill_resolves_with_matching_kind_cost_and_effects`: replace `self.assertFalse(is_freeform_eligible(skill))` with a check that names the real gate:

```python
# Freeform scaling needs the element's mastery passive (freeform_mastery_entitled);
# a monster kit never declares one, so shape eligibility grants no scale.
if skill.element is not None:
    self.assertNotIn(
        f"{skill.element.key}_mastery",
        (*variant.active_skill_keys, *variant.passive_skill_keys),
    )
```

and drop the now-unused `is_freeform_eligible` import if nothing else uses it.

2. Representative smoke:

New `world/rules/tests/test_ember_bristle_boar_resource_skill.py`, first line `"""Data-contract test: boar two-strike representative-composition production smoke over the generic area/single damage and payment contracts`, `REPRESENTATIVE_VARIANT = "warm_den_boar"`, deriving keys and costs from declarations. Observations, each naming its defect: against one real opponent the shipped policy selects the single-target skill; against two opponents it selects the area skill; the resolved sweep reaches every living enemy with separately recorded hit and defense outcomes, leaves an allied monster control untouched and pays MP and SP once; exhausting either resource falls back to the innate attack; `freeform_scales_for(<constructed boar>, SKILL_REGISTRY[<each kit key>]) == ()` (detects a monster gaining freeform scaling); a committed reload preserves spent resources, kit and binding. Register in shard `rules-6`; add the `tools/test_data_freeze.json` contract entry.

## Risks / Trade-offs

- [First all-damage elemental monster kit is freeform shape-eligible] → entitlement, not shape, gates scaling; D7 asserts the entitlement precondition at declaration level and observes an empty ladder on a constructed boar.
- [Legacy never mixes skills against one enemy] → acceptable: the area strike is reachable whenever a party stands, as the design intends.

## Verification

Focused labels: `world.rules.tests.test_ember_bristle_boar_resource_skill`, `world.rules.tests.test_monster_composition_coverage`, `AuthoredMonsterKitContractTests`, `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_bestiary_documentation`, `world.lore.tests.test_monster_visuals`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests` (fingerprint unchanged). Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate ember-bristle-boar-species --strict`, `uv run --locked python -m tools.contract_gate`.
