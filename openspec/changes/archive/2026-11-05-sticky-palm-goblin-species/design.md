# Design

## Context

See proposal.md (Why). Shared delivery facts are in `mudfilm-slime-species` design D1–D8. Specific facts:

- Shipped enemy hit-rider group signature `(("active","damage","enemies",None),("active","buff_apply","enemies",0))`; its sorted-minimum representative `cliff_stepper` is declared in `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py`, which reads the live modifier row's axis. `"cliff_stepper" < "hanging_nest_forager"`, so nothing moves.
- Precedents for this kit: `martial_hamstring` (elementless `damage:none:physical` + agility debuff) and `rock_echo_ram` (`buff_apply:rock_echo_stagger`, `agility_flat` debuff with `requires_hit_from=0`).
- After the slime change, the kit-contract test asserts `spell_tier_for(skill) is None` for elementless kits; this skill relies on that.

## Goals / Non-Goals

**Goals:** one complete, constructible low-tier species, AI-usable in legacy mode, with keyed documentation.

**Non-Goals:** immobilization, theft, equipment effects, nest-building or material-collection mechanics (design §5); cohesive group placement (owned by `weak-species-habitats` and the transfer-station change); beastfolk or civilized-people modelling.

## Decisions

### D1. Species row (append after `wax_pouch_rat`)

- `key="sticky_palm_goblin"`, `display_name_zh="膠掌小鬼"`; published fields: design §4.2's three quoted passages verbatim; `habitat_tags=("western_hills_valleys",)`.
- `author_hidden_truth_zh="（作者私有：隱秘真相）本物種沒有已定的起源真相；掌部黏液的成因不在設定中交代。"`
- `author_explanation_zh="（作者私有：作者解釋）低階社群型魔物：短效掌部黏液支撐懸掛巢、攀附與輕小巢材收集；溝通限於動物式啼叫、敲擊與學習而來的物件使用，與獸人族的登錄與描寫分開。戰鬥呈現為抓扯與命中後短暫的動作節奏干擾。"`
- `author_conjecture_zh="（作者私有：尚未證實的猜想）採石工人說膠掌小鬼會模仿人類的敲擊節奏，這種說法尚未證實。"`
- `default_variant_key="hanging_nest_forager"`, `ordinary_variant=True`.

### D2. Variant row (append after `wax_cache_forager`)

`MonsterVariant("hanging_nest_forager", "sticky_palm_goblin", "懸巢型", "普通版本，在岩棚與灌木間搬運巢材、維護懸掛巢。", "low", True, MonsterCombatProfile(...), "F", True, active_skill_keys=("sticky_palm_grab",), passive_skill_keys=(), behaviour_profile_key="instinctive")`. Profile: all axes inside the low band, `magic_power=0`, `sp` at least twice the skill cost, `mp` any non-negative literal.

### D3. Skill row

```python
_skill(
    "sticky_palm_grab",
    "黏掌抓扯",
    "以黏亮寬掌抓扯單一敵方目標，造成物理傷害；命中後使對手短暫失去動作節奏，降低其敏捷。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"sp": <positive int literal>},
    usable_out_of_combat=True,
    effects=["damage:none:physical", "buff_apply:sticky_palm_drag"],
    category=SkillCategory.MARTIAL_ARTS,
    faction_constraint=FactionConstraint.ANY,
    eligibility=SkillEligibility(
        allowed_actor_kinds=("monster",),
        allowed_species=("sticky_palm_goblin",),
    ),
    prerequisites=(),
    effect_policies=(
        EffectPolicy(coefficient=<float literal>, audience=EffectAudience.ENEMIES),
        EffectPolicy(coefficient=1.0, audience=EffectAudience.ENEMIES, requires_hit_from=0),
    ),
)
```

`usable_out_of_combat=True` follows the settled ruling for damage-carrying monster abilities. The damage coefficient stays within the range used by shipped low-tier monster abilities.

### D4. Timed effect and presentation

- `buffs.yaml`: `key: sticky_palm_drag`, positive `duration` of the same order as `rock_echo_stagger`, `stacking: refresh`, `polarity: debuff`, `modifiers: {}`.
- `combat_modifiers.yaml`: `id: sticky_palm_drag_agility_flat`, `when: {buff_active: sticky_palm_drag}`, `then: {agility_flat: <negative int>}`, magnitude no larger than `rock_echo_stagger_agility_flat`'s.
- `status_display.yaml`: `sticky_palm_drag` 黏掌抓扯 `harmful`; `sticky_palm_drag_agility_flat` 黏掌抓扯敏捷下降 `harmful`.
- `data_martial.py`: `NarrationRow("sticky_palm_grab", action=("{actor} 張開黏亮的寬掌，一把扯向對手的手臂。", "{actor} 攀低身形，細長手指拽住對方的衣角猛力一拉。"))`.

### D5. AI and evidence

No `monster_behaviour.yaml` edit: `instinctive` legacy selects the damage-bearing kit and keeps the inclusive flee threshold. Re-fingerprint per `mudfilm-slime-species` D5 steps 1–4 without changing `activated`/`activation_bindings` (only `configuration_fingerprint`, the rollback fingerprint, the selector evidence entry and README fingerprint lines move).

### D6. Bestiary, ledger, review

- Overview row `| 低階 | 膠掌小鬼 | 丘陵灌木、廢棄採石地與岩棚 | 短效掌部黏液支撐懸掛巢與攀附 | 懸巢型 |`.
- `### 膠掌小鬼` section at the end of `## 低階魔物` with a `bestiary` block (species/parent `sticky_palm_goblin`, sole variant `hanging_nest_forager` `delivered`, six public fields, status `delivered`) and affirmative paragraphs **原型與棲地。**, **外觀。**, **生態與在地關係。**, **戰鬥中的表現。**, variant row `| 懸巢型 | 普通版本，在岩棚與灌木間搬運巢材、維護懸掛巢 |`.
- Ledger row for `sticky_palm_goblin`, including that the depiction stays an animal-level monster distinct from beastfolk.
- Review section "膠掌小鬼" in `docs/development/monster-content-expansion.md`, including one non-gating low-tier role observation and an evidence-map line that the hit-rider and fault-rollback vectors are owned by the shared rider suites and representative `cliff_stepper`.

### D7. Tests

Only `test_rule_sticky_palm_drag_agility_flat` (four-line precedent). Movement/flee preservation is owned by the shared rider and flee suites; no clone.

## Risks / Trade-offs

- [Legacy first_owned always picks the grab while affordable] → intended; SP exhaustion falls back to the innate attack under the existing contract.

## Verification

Focused labels as listed in `wax-pouch-rat-species` design Verification, replacing the slime smoke with `world.rules.tests.test_sway_whistle_sparrow_resource_skill`. Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate sticky-palm-goblin-species --strict`, `uv run --locked python -m tools.contract_gate`.
