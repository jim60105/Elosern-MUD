# Design

## Context

See proposal.md (Why). Facts at `1b1be7b8` this design relies on:

- `world/lore/monster_species.py` validates `_SPECIES_DECLARATIONS`/`_VARIANT_DECLARATIONS` at import: bands from `MONSTER_TIER_REGISTRY["low"]` (HP, attack, agility, defense, magic `(0, 0)`), grade inside the tier's guild rank range, default variant ordinary and owned. MP/SP have no band.
- `world/lore/tests/test_monster_species_content.py` requires `author_hidden_truth_zh` to contain 「沒有已定」, `author_explanation_zh` to contain 「作者解釋」, `author_conjecture_zh` to contain 「尚未證實」, and forbids registry strings naming a skill, behaviour or trait key.
- `world/skills/tests/test_skill_registry/test_registry_contract.py::AuthoredMonsterKitContractTests.test_every_declared_kit_skill_resolves_with_matching_kind_cost_and_effects` asserts `self.assertTrue(spell_tier_for(skill))` for every active kit skill. `world/skills/cost_tiers.py::spell_tier_for` returns `None` for any skill without an element or without an `mp` cost, so an SP-only elementless kit skill fails that assertion although the `monster-resource-abilities` contract only applies the cost-tier gate where it exists. The same test requires `allowed_species` to equal the set of declaring species, positive integer costs in `{"mp", "sp"}`, parallel `effect_policies`, and `is_freeform_eligible(skill) is False`.
- `world/skills/narration/validation.py::validate_catalog` requires a narration row for every active skill whose category is not pending; `world/rules/status_display.py` rejects any buff or modifier rule without a `status_display.yaml` code; `world/rules/tests/test_combat_modifiers.py` holds one `test_rule_<id>` per modifier row.
- `world/rules/tests/test_monster_composition_coverage.py` groups kit-delivering variants by ordered `(slot, effect family, audience, requires_hit_from)` and requires exactly one module declaring `REPRESENTATIVE_VARIANT = <sorted-minimum key>` per group. This kit's signature `(("active", "self_buff_apply", "self", None),)` matches no shipped group, so this change owns a new representative; `wax_cache_forager` (rat) joins it later and `mudbank_dweller` stays the sorted minimum.
- The legacy decision body proposes only damage-bearing actives; the utility path proposes `SELF_ONLY` support skills and values a `defense` mount as control. `owned-kit-decision-coverage` adds `support_kit_mode_violations`, whose shipped check fails unless this variant resolves utility.
- `world/rules/monster_behaviour.py::_tuning_fingerprint` covers every buff definition, every modifier rule, `variant_intelligence`, `variant_decision_mode` and named bindings, so this change moves the startup fingerprint; `world/rules/tests/test_monster_ai_activation.py` compares it with `docs/development/monster-ai-activation-evidence/activation.json` (precedent: commit `1a141247` re-fingerprinted after the fatigue buffs).

## Goals / Non-Goals

**Goals:** one complete, constructible, AI-usable low-tier species with its keyed documentation.

**Non-Goals:** placement, activity, compositions (owned by `weak-species-habitats`); other species; a skill passive; terrain mutation, mud accumulation or any channel/irrigation mechanic (design §5); changing the legacy body or any other variant's binding; image assets.

## Decisions

### D1. Species row (append after the crocodile in `_SPECIES_DECLARATIONS`)

- `key="mudfilm_slime"`, `display_name_zh="泥膜史萊姆"`.
- `published_description_zh`, `published_appearance_zh`, `published_ecology_zh`: the three quoted passages of design §4.1 (公開描述, 外觀, 生態與在地關係) copied verbatim.
- `habitat_tags=("eastern_plains", "western_hills_valleys")`.
- `author_hidden_truth_zh="（作者私有：隱秘真相）本物種沒有已定的起源真相；泥膜的成因不在設定中交代。"`
- `author_explanation_zh="（作者私有：作者解釋）低階防禦型濕地物種：體表附著的細泥收縮成護膜，生態連結窄分水口的淤積；戰鬥呈現為自身護膜與接觸撞擊。棲地限於明確宣告的陰濕地塊。"`
- `author_conjecture_zh="（作者私有：尚未證實的猜想）農人傳說泥膜史萊姆停留過的渠口特別清澈，這種說法尚未證實。"`
- `default_variant_key="mudbank_dweller"`, `ordinary_variant=True`.

### D2. Variant row (append after `bay_warden`)

`MonsterVariant("mudbank_dweller", "mudfilm_slime", "濕岸型", "普通版本，貼著潮濕溝岸與滲水洞口覓食。", "low", True, MonsterCombatProfile(...), "F", True, active_skill_keys=("mudfilm_guard",), passive_skill_keys=(), behaviour_profile_key="instinctive")`.

Profile literals are authored here once and nowhere else (design §6). Constraints the author applies when choosing them: every axis inside `MONSTER_TIER_REGISTRY["low"]`'s bands; `magic_power=0`; slow means `agility` no greater than the lowest `agility` among shipped low-tier ordinary variants; defensive means `defense` no lower than the highest `defense` among shipped low-tier ordinary variants; `sp` at least twice the skill's SP cost so a refresh can be observed; `mp` any non-negative literal (the kit spends none). Record the chosen literals' rationale in the review document (D8) without copying them into a table.

### D3. Skill row (append to `world/skills/registry/data_monster_abilities.py::ROWS`)

```python
_skill(
    "mudfilm_guard",
    "泥膜收束",
    "收緊體表附著的泥膜，短暫提高自身防禦。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"sp": <positive int literal>},
    usable_out_of_combat=False,
    effects=["self_buff_apply:mudfilm_shell"],
    category=SkillCategory.MARTIAL_ARTS,
    faction_constraint=FactionConstraint.SELF_ONLY,
    eligibility=SkillEligibility(
        allowed_actor_kinds=("monster",),
        allowed_species=("mudfilm_slime",),
    ),
    prerequisites=(),
    effect_policies=(EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),),
)
```

No element (it is a body action, not magic), so no magic tier and no freeform eligibility. `usable_out_of_combat=False`: the earlier ruling requiring `True` covers damage-carrying monster abilities only; a combat modifier has no field use. Update the module docstring's composition list with one sentence for this self-only support shape.

### D4. Timed effect and presentation

- `world/rules/rulebook/buffs.yaml`, after `mane_misdirection`: `key: mudfilm_shell`, `duration: <positive int seconds>`, `stacking: refresh`, `polarity: buff`, `modifiers: {}`, with a Traditional Chinese comment in the existing style. Choose a duration of the same order as the shipped self guards `lamp_carapace_guard` and `ridge_brace`.
- `world/rules/rulebook/combat_modifiers.yaml`: `id: mudfilm_shell_defense`, `when: {buff_active: mudfilm_shell}`, `then: {defense: <positive int>}`, no larger than the largest shipped low-tier self-guard defense contribution.
- `world/rules/rulebook/status_display.yaml`: `code: mudfilm_shell` label 泥膜收束 severity `beneficial`; `code: mudfilm_shell_defense` label 泥膜收束防禦提升 severity `beneficial`.
- `world/skills/narration/data_martial.py`: append `NarrationRow("mudfilm_guard", action=("{actor} 縮起膠質身軀，體表細泥壓成一層深色薄膜。", "{actor} 收緊外膜，泥紋沿著身體聚成環帶。"))`. Lines describe the attempt only (module convention).

Repeated casts refresh lifetime through the shared `stacking: refresh` rule; no magnitude accumulates.

### D5. AI binding and activation evidence

In `world/rules/rulebook/monster_behaviour.yaml` add `variant_intelligence: mudbank_dweller: 20` (comment: 濕岸型 only tightens its film when pressed and bumps back at short range; reflexive self-protection is the least decision depth of any activated variant) and `variant_decision_mode: mudbank_dweller: utility`. Known trade-off: utility variants never choose flee (`monster-flee-policy`); the slime's retreat-orientation is expressed by its passive field aggression in `weak-species-habitats`.

Re-fingerprint, following commit `1a141247`:
1. Run `uv run --locked python tools/monster_ai_manual_reports.py selector` and copy `.var/monster-ai-manual-reports/selector-check.json` and `.md` over `docs/development/monster-ai-manual-evidence/` (margin must still be met; record the paired difference).
2. Read the new startup fingerprint from the regenerated `selector-check.json` (`configuration_fingerprint`) and the rollback fingerprint by running `RollbackTests` once (its failure message prints the actual value) or `uv run --locked --env-file=/tmp/mud-field-tests.env evennia shell --settings test_settings.py -c "from world.rules.tests.test_monster_ai_activation import _legacy_edited_tuning; print(_legacy_edited_tuning().fingerprint)"`.
3. Update `activation.json`: `configuration_fingerprint`, `activated.mudbank_dweller: 20`, `activation_bindings.mudbank_dweller: ["low", "instinctive"]`, `legacy_rollback.configuration_fingerprint`, the `selector-check.json` evidence entry's fingerprint; archetype/performance entries keep their own campaign fingerprints.
4. Update `docs/development/monster-ai-activation-evidence/README.md` (activated table row with rationale, fingerprint lines) and the selector paragraph of `docs/development/monster-ai-manual-evidence/README.md`.

### D6. Bestiary and ledger

`docs/lore/bestiary.md`:
- Header: after the 2026-10-05 approval paragraph add 「**第三批核准：**2026-11-03 起，[魔物內容擴充設計](/superpowers/specs/2026-11-03-monster-content-expansion-design) 另行核准三種低階物種、吞潮鱷的高階變體與一種高階物種；各物種逐一收錄於下方現行小節。」 This note is added once here; later changes do not edit it.
- Overview table row: `| 低階 | 泥膜史萊姆 | 潮濕溝岸、舊灌溉支渠與滲水洞口 | 細泥收縮成可摺疊的護膜 | 濕岸型 |`.
- New `### 泥膜史萊姆` section at the end of `## 低階魔物` (before `## 中階魔物`) with:

```bestiary
species: mudfilm_slime
parent-species: mudfilm_slime
default-variant: mudbank_dweller
variants:
  - key: mudbank_dweller
    status: delivered
public-fields:
  - display_name_zh
  - published_description_zh
  - published_appearance_zh
  - published_ecology_zh
  - habitat_tags
  - description_zh
status: delivered
```

then affirmative paragraphs headed **原型與棲地。**, **外觀。**, **生態與在地關係。**, **戰鬥中的表現。** (the last describes the film tightening and short impact in body/behaviour terms, never naming keys or fields), the variant table `| 濕岸型 | 普通版本，貼著潮濕溝岸與滲水洞口覓食 |`, and an optional affirmative **委託背景示例。** set at a farm's narrow channel mouth.

`docs/development/bestiary-editorial-review.md`: append `| `mudfilm_slime` | <implementation date> | <ecology read> | <ability scope read against the declared self-guard kit> | <current section read as current; no historical appendix> | <disposition> |`, each cell a real read in the style of the existing rows, and stating the affirmative-prose read.

### D7. Tests

1. `test_registry_contract.py`: replace `self.assertTrue(spell_tier_for(skill))` with:

```python
if skill.element is not None and "mp" in skill.cost:
    # An elemental MP kit skill must classify into a magic tier.
    self.assertTrue(spell_tier_for(skill))
else:
    # A body action without element or MP cost carries no magic tier.
    self.assertIsNone(spell_tier_for(skill))
```

2. `test_combat_modifiers.py::CombatModifierTests`: add `test_rule_mudfilm_shell_defense` copying `test_rule_grain_rattle_accuracy`'s four lines with the new rule id.
3. New `world/rules/tests/test_mudfilm_slime_resource_skill.py`, first docstring line exactly `"""Data-contract test: slime representative-composition production smoke over the generic self-support/lifetime contracts`, declaring `REPRESENTATIVE_VARIANT = "mudbank_dweller"` and deriving `REPRESENTATIVE_ROW`, `SKILL_KEY`, mounted `BUFF_KEY` and the live modifier row from declarations (pattern: `test_tide_lamp_crab_resource_skill.py`). It constructs the representative with `construct_species_individual(REPRESENTATIVE_ROW.species_key, REPRESENTATIVE_VARIANT)`, one real `PlayerCharacter` opponent and one constructed monster ally as a control in a real battlefield, and observes:
   - `monster_behaviour_policy(..., trace=sink)` under the shipped tuning records a `TracePlan` whose `skill_key == SKILL_KEY` targeting only the caster, with positive `control` (detects a legacy binding or a non-candidate kit);
   - resolving that plan's request through `ActionResolver` pays the skill's SP once, mounts `BUFF_KEY` on the caster only, and changes the caster's evaluated modifier axis named by the live row while the opponent and ally are unchanged (detects recipient routing);
   - aging the mount through `WorldClock` and recasting refreshes one contribution, and expiry removes it (detects stale refresh lifetime);
   - with current SP below the cost, the trace has no plan for `SKILL_KEY` and a forced request is rejected with no payment (detects fabricated payment);
   - after a committed reload, spent SP, the mount's remaining lifetime, kit and binding persist.
   Register the module once in `.github/evennia-shards.json` shard `rules-6` next to `world.rules.tests.test_tide_lamp_crab_resource_skill`, and add `{"path": "world/rules/tests/test_mudfilm_slime_resource_skill.py", "reason": "slime representative-composition production smoke over the generic self-support/lifetime contracts"}` to `tools/test_data_freeze.json` `contract`.

### D8. Roster-free wording and review document

In `world/lore/monster_species.py`, rewrite the module docstring phrase 「six frozen `MonsterSpecies` rows and twelve frozen `MonsterVariant` rows」 and the authoring comment's 「all twelve」 claims into count-free statements. Create `docs/development/monster-content-expansion.md` ("Monster Content Expansion: Developer Review and Evidence") with a section "泥膜史萊姆" recording: the role constraints of D2 and how the chosen literals satisfy them (relations, not a value table), intelligence rationale, the flee trade-off, focused commands and results, and the human-review status of the prose.

## Risks / Trade-offs

- [Utility selection rarely chooses the guard] → the smoke asserts candidacy and value, not frequency; balance edits stay single-source.
- [Fingerprint churn] → each later content change repeats D5; the chain is serial.

## Verification

`/tmp/mud-field-tests.env` with `MUD_TEST_SETTINGS=1`; `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <label>` one class at a time (≤100 tests): `world.rules.tests.test_mudfilm_slime_resource_skill`, `world.rules.tests.test_monster_composition_coverage`, `world.skills.tests.test_skill_registry.test_registry_contract.AuthoredMonsterKitContractTests`, `world.rules.tests.test_combat_modifiers.CombatModifierTests`, `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `...ActivationBindingTests`, `...RollbackTests`, `world.lore.tests.test_monster_visuals`. Then `uv run --locked python -m tools.map_reference_context` and `--check`, `openspec validate mudfilm-slime-species --strict`, `uv run --locked python -m tools.contract_gate`. Production smoke here is the representative module; complete evidence and browser suites stay CI-owned.
