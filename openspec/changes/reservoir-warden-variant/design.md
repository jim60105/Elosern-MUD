# Design

## Context

See proposal.md (Why). Shared delivery facts are in `mudfilm-slime-species` design D1–D8. Specific facts at `1b1be7b8`:

- `tide_devouring_bite` declares `TargetSpec.SINGLE`, `cost={"mp": 10, "sp": 5}`, `effects=["damage:water:physical", "gauge_transfer:mp:drain:fixed:10"]`, the transfer policy `requires_hit_from=0` with `GaugeTransferPolicy(caster_recovery_share=1.0)`, and `allowed_species=("tide_devouring_crocodile",)`. It is reused unchanged; the kit-contract test requires `allowed_species` to equal the declaring species, which stays `{"tide_devouring_crocodile"}`.
- `MONSTER_TIER_REGISTRY["high"]`: guild rank range `("B", "A")`, magic band `(0, 0)`.
- `spell_tier_for` resolves an elemental MP skill only when its MP cost lies inside an `MP_COST_TIERS` band for its column (`SELF` counts as single); `is_freeform_eligible` is `False` for any skill with a `self_buff_apply` effect.
- The crocodile's current `published_ecology_zh` contains negative boundary sentences and names the field `magic_power`; design §2 requires the related current section to be rewritten affirmatively while preserving meaning.
- New composition signature `(("active","damage","enemies",None),("active","gauge_transfer","enemies",0),("active","self_buff_apply","self",None))`; no shipped group matches it.

## Goals / Non-Goals

**Goals:** one complete standalone high-tier variant with a usable two-skill kit and an affirmative crocodile publication.

**Non-Goals:** placement and the boss site; any change to `bank_lurker`, `bay_warden`, `tide_devouring_bite`, the existing `tide_mouth_boss_site`, or the crocodile's habitat; world-tide manipulation, long-range drain or passive healing (design §5); quest commissions.

## Decisions

### D1. Variant row (append after the last shipped variant)

`MonsterVariant("reservoir_warden", "tide_devouring_crocodile", "蓄潮型", <design §4.4 公開變體描述 verbatim>, "high", False, MonsterCombatProfile(...), "A", True, active_skill_keys=("tide_devouring_bite", "reservoir_guard"), passive_skill_keys=(), behaviour_profile_key="ambush_predator")`.

Profile constraints: every axis inside `MONSTER_TIER_REGISTRY["high"]`; `magic_power=0`; the stronger-variant role means each physical axis and HP is no lower than the same axis of `bay_warden`; `mp` no lower than the sum of both skills' MP costs so the variant can alternate drain and guard; `sp` at least twice the bite's SP cost.

### D2. Skill row

```python
_skill(
    "reservoir_guard",
    "蓄潮護膜",
    "以自身魔力讓頸側與背脊的薄水膜貼合鱗甲，短暫提高自身防禦。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    cost={"mp": <positive int inside an MP_COST_TIERS single band>},
    usable_out_of_combat=False,
    element="water",
    effects=["self_buff_apply:reservoir_film"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="water",
    faction_constraint=FactionConstraint.SELF_ONLY,
    eligibility=SkillEligibility(
        allowed_actor_kinds=("monster",),
        allowed_species=("tide_devouring_crocodile",),
    ),
    prerequisites=(),
    effect_policies=(EffectPolicy(coefficient=1.0, audience=EffectAudience.SELF),),
)
```

Only `reservoir_warden` declares it, so `bank_lurker`/`bay_warden` never own it although they share the species.

### D3. Timed effect and presentation

- `buffs.yaml`: `key: reservoir_film`, positive `duration` of the same order as the shipped self guards, `stacking: refresh`, `polarity: buff`, `modifiers: {}`.
- `combat_modifiers.yaml`: `id: reservoir_film_defense`, `when: {buff_active: reservoir_film}`, `then: {defense: <positive int>}`; record in the review document why the magnitude suits the high tier's defense band.
- `status_display.yaml`: `reservoir_film` 蓄潮護膜 `beneficial`; `reservoir_film_defense` 蓄潮護膜防禦提升 `beneficial`.
- `world/skills/narration/data_water.py`: `NarrationRow("reservoir_guard", action=("{actor} 收緊頸側皺褶，一層薄水膜沿著鱗甲鋪開。", "{actor} 低伏在水線上，背脊的水紋聚成一片貼身的光膜。"))`.

### D4. AI binding and evidence

`monster_behaviour.yaml`: `variant_intelligence: reservoir_warden: 62` (comment: 蓄潮型 weighs drawing an opponent's magic against spending its own on the film — a recurring trade-off read from its own resources) and `variant_decision_mode: reservoir_warden: utility`. Re-fingerprint per `mudfilm-slime-species` D5 steps 1–4 with `activated.reservoir_warden: 62` and `activation_bindings.reservoir_warden: ["high", "ambush_predator"]`. Trade-off recorded in the review as a known deviation from design §5/§7.3: under `monster-flee-policy` a utility-mode monster never voluntarily flees, so this boss never AI-flees; its escapes in play come from the opposing party's paid retreat. Reverting it to legacy would make its guard unusable (`owned-kit-decision-coverage`).

### D5. Affirmative crocodile publication

- `MonsterSpecies("tide_devouring_crocodile", …).published_ecology_zh` becomes (draft; editorial wording may change within this meaning): 「牠在接觸活物時，透過水屬性力量吸取對方的部分魔力。施法者與牠纏鬥時，常先察覺魔力消耗異常，再意識到危險。牠依靠咬合與伏擊捕食，吸取發生在咬合接觸的瞬間；被吸走的是對方當下可用的魔力，休息後便會回復，吞潮鱷則把吸得的魔力納入自己的儲備。」 Other species fields stay unchanged.
- `docs/lore/bestiary.md` crocodile section: add `- key: reservoir_warden` / `status: delivered` to the `bestiary` block; rewrite **特殊生態。** to the new field text; replace the **能力邊界。** paragraph with **戰鬥中的表現。** describing close-contact drain and, for 蓄潮型, the self-funded film, in affirmative body/behaviour terms; add a **蓄潮型。** block with the three §4.4 variant passages verbatim (description, appearance, ecology including 「閉灣者」); add variant row `| 蓄潮型 | 長期占據偏遠潮汐支流的深灣，於吸取魔力與護住身體之間取捨 |`; overview row becomes `| 中階／高階 | 吞潮鱷 | … | … | 潛岸型、守灣型、蓄潮型 |` keeping its other cells.
- Ledger: update the `tide_devouring_crocodile` row (new date, faces read against the drain-plus-guard kit, affirmative rewrite read, current/historical separation).
- Review section "吞潮鱷・蓄潮型" in `docs/development/monster-content-expansion.md`.

### D6. Tests

- `test_rule_reservoir_film_defense` in `CombatModifierTests` (four-line precedent).
- New `world/rules/tests/test_reservoir_warden_resource_skill.py`, first line `"""Data-contract test: crocodile drain-and-guard representative-composition production smoke over the generic transfer/self-support/lifetime contracts`, `REPRESENTATIVE_VARIANT = "reservoir_warden"`, deriving both skill keys, costs, the mounted buff and the live modifier row from declarations. Observations, each naming the defect it detects: the shipped utility trace for a constructed representative facing one real opponent contains plans for both kit skills; a resolved bite on a hit lowers the opponent's current MP by the actual removed amount and raises the caster's by the credited amount capped at its maximum, then pays the bite's costs; a resolved guard pays its MP once from the caster's current pool and mounts the buff on the caster only (opponent and an ally control unchanged); with current MP below the guard cost but above zero, the trace has no guard plan and a forced guard request is rejected with unchanged resources; a committed reload preserves spent MP/SP, the mount, kit and binding. Register in shard `rules-6`; add the matching `tools/test_data_freeze.json` contract entry.

## Risks / Trade-offs

- [Boss never AI-flees] → documented; `high-tier-boss-sites` exercises party retreat and re-engagement instead.
- [Rewrite drifts from approved meaning] → the ledger records the read; the draft states each original limit positively (contact, available magic, recovery, credit to its own reserve).

## Verification

Focused labels (one per run): `world.rules.tests.test_reservoir_warden_resource_skill`, `world.rules.tests.test_crocodile_resource_skill`, `world.rules.tests.test_monster_composition_coverage`, `AuthoredMonsterKitContractTests`, `CombatModifierTests`, `world.lore.tests.test_monster_species_content`, `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_ai_activation.ActivationRecordTests`, `...ActivationBindingTests`, `...RollbackTests`, `world.rules.tests.test_human_combat_calibration` classes that construct the crocodile. Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate reservoir-warden-variant --strict`, `uv run --locked python -m tools.contract_gate`. Record in the review section, as non-gating observations: one smoke encounter outcome against the A-grade role; and for the newly activated variant the trace's candidate count, exclusions and whether the guard was selected over a short seeded run (expansion evidence for `monster-ai-rollout::expansion-and-retuning-require-affected-evidence`). Payment/effect fault rollback for the new kit is owned by the shared generic suites; say so in the evidence map.
