# Design

## Context

See proposal.md (Why). This change follows the delivery pattern `mudfilm-slime-species` establishes (read its design D1–D8 for the shared facts: registry validation and private-note markers, kit-contract test, narration/status/one-test-per-rule contracts, composition-coverage grouping, fingerprint coverage and the `1a141247` re-fingerprint procedure). After that change, the self-support group `(("active", "self_buff_apply", "self", None),)` has representative `mudbank_dweller`; `"mudbank_dweller" < "wax_cache_forager"`, so the representative does not move and no test module is added.

## Goals / Non-Goals

**Goals:** one complete, constructible, AI-usable low-tier species with keyed documentation.

**Non-Goals:** placement or activity; grain wrapping, food preservation, inventory transfer or narrow-gap movement mechanics (design §5: the agility improvement changes modifiers only); any change to the slime's smoke.

## Decisions

### D1. Species row (append after `mudfilm_slime`)

- `key="wax_pouch_rat"`, `display_name_zh="蠟囊鼠"`; published description, appearance and ecology: the three quoted passages of design §4.3 verbatim; `habitat_tags=("eastern_plains", "western_hills_valleys")`.
- `author_hidden_truth_zh="（作者私有：隱秘真相）本物種沒有已定的起源真相；頰囊薄蠟的成因不在設定中交代。"`
- `author_explanation_zh="（作者私有：作者解釋）低階家族型鼠類：頰囊薄蠟為穀團短期防潮、腹側蠟層支持窄縫滑行，連結荒廢糧站與運糧道；戰鬥呈現為咬擊與自身短暫敏捷提升。"`
- `author_conjecture_zh="（作者私有：尚未證實的猜想）糧站工人相信蠟封穀團能保存一整季，這種說法尚未證實。"`
- `default_variant_key="wax_cache_forager"`, `ordinary_variant=True`.

### D2. Variant row (append after `mudbank_dweller`)

`MonsterVariant("wax_cache_forager", "wax_pouch_rat", "藏穀型", "普通版本，以頰囊蠟膜裹住穀粒，藏進潮濕巢穴。", "low", True, MonsterCombatProfile(...), "F", True, active_skill_keys=("wax_pouch_slip",), passive_skill_keys=(), behaviour_profile_key="instinctive")`.

Profile constraints: all axes inside `MONSTER_TIER_REGISTRY["low"]`; `magic_power=0`; fast means `agility` no lower than the highest `agility` among shipped low-tier ordinary variants; `sp` at least twice the skill cost; `mp` any non-negative literal.

### D3. Skill row

Identical shape to `mudfilm_guard` (TargetSpec.SELF, `FactionConstraint.SELF_ONLY`, no element, `SkillCategory.MARTIAL_ARTS`, `usable_out_of_combat=False`, one `EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF)`) with key `wax_pouch_slip`, label 滑蠟翻身, description 「把腹側薄蠟抹勻後靈巧翻身，短暫提高自身敏捷。」, `cost={"sp": <positive int>}`, `effects=["self_buff_apply:wax_slip"]`, `allowed_species=("wax_pouch_rat",)`.

### D4. Timed effect and presentation

- `buffs.yaml`: `key: wax_slip`, positive `duration` of the same order as the shipped self guards, `stacking: refresh`, `polarity: buff`, `modifiers: {}`.
- `combat_modifiers.yaml`: `id: wax_slip_agility_flat`, `when: {buff_active: wax_slip}`, `then: {agility_flat: <positive int>}`; magnitude no larger than the absolute value of the shipped `rock_echo_stagger_agility_flat` contribution.
- `status_display.yaml`: `wax_slip` 滑蠟翻身 `beneficial`; `wax_slip_agility_flat` 滑蠟翻身敏捷提升 `beneficial`.
- `data_martial.py`: `NarrationRow("wax_pouch_slip", action=("{actor} 壓低圓身，抹著薄蠟的腹側一滑，身形倏地翻轉。", "{actor} 鼓起頰囊，順勢側翻，長尾貼著身後掃過。"))`.

### D5. AI binding and evidence

`monster_behaviour.yaml`: `variant_intelligence: wax_cache_forager: 30` (comment: 藏穀型 times its slip around a defended cache and family foraging — a little more situational reading than the slime's reflexive film) and `variant_decision_mode: wax_cache_forager: utility`. Re-fingerprint exactly as `mudfilm-slime-species` D5 steps 1–4, adding `activated.wax_cache_forager: 30` and `activation_bindings.wax_cache_forager: ["low", "instinctive"]`. Utility never flees; retreat-orientation is the field aggression authored by placement changes.

### D6. Bestiary, ledger, review

- Overview row `| 低階 | 蠟囊鼠 | 平原田界、荒廢糧站與丘陵運糧道 | 頰囊薄蠟裹住穀粒防潮 | 藏穀型 |`.
- `### 蠟囊鼠` section at the end of `## 低階魔物` with a `bestiary` block (species/parent `wax_pouch_rat`, default and sole variant `wax_cache_forager` `delivered`, the same six public fields, status `delivered`) and affirmative paragraphs **原型與棲地。**, **外觀。**, **生態與在地關係。**, **戰鬥中的表現。**, variant table row `| 藏穀型 | 普通版本，以頰囊蠟膜裹住穀粒，藏進潮濕巢穴 |`.
- Ledger row for `wax_pouch_rat` with real per-face reads and the affirmative-prose read.
- `docs/development/monster-content-expansion.md`: section "蠟囊鼠" (role relations, intelligence rationale, reuse of the self-support representative, focused results).

### D7. Tests

Only `test_rule_wax_slip_agility_flat` in `CombatModifierTests` (four-line precedent). All other evidence is generic or the slime representative.

## Risks / Trade-offs

- [The representative observes defense, not agility] → shape grouping deliberately excludes the modifier axis; shared synthetic lifetime/recipient suites own the mechanism and the correspondence test pins only that the rule is reachable from its buff.

## Verification

Focused labels (one per run, `/tmp/mud-field-tests.env`): `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_bestiary_documentation`, `world.lore.tests.test_monster_visuals`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.rules.tests.test_monster_composition_coverage`, `world.rules.tests.test_mudfilm_slime_resource_skill`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `...ActivationBindingTests`, `...RollbackTests`. Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate wax-pouch-rat-species --strict`, `uv run --locked python -m tools.contract_gate`.
