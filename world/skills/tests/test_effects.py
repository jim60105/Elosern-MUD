"""Unit tests for the typed skill effect parser."""

from tools.spec_traceability import covers_requirement

import unittest

from world.skills.effects import (
    BuffApplyEffect,
    CleanseEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DamageEffect,
    DisengageEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    ElementMasteryEffect,
    FlavorEffect,
    GrowthRateEffect,
    HealEffect,
    MovementEffect,
    RuleTableEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualEventEffect,
    SexualMasteryEffect,
    StatMultiplyEffect,
    WeaponStyleEffect,
    parse_effect,
)


class ParseEffectTests(unittest.TestCase):
    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_stat_multiply_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("stat_multiply:atk_phys:100"),
            StatMultiplyEffect(trait="atk_phys", multiplier=100.0),
        )

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_growth_rate_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("growth_rate:magic:100"),
            GrowthRateEffect(stat="magic", multiplier=100.0),
        )

    def test_element_mastery_rank_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("element_mastery_rank:主宰"),
            ElementMasteryEffect(rank="主宰"),
        )

    def test_sexual_magic_mastery_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("sexual_magic_mastery"), SexualMasteryEffect())

    def test_passive_buff_parses_into_a_rule_table_effect(self):
        self.assertEqual(
            parse_effect("passive_buff:defense_small"),
            RuleTableEffect(rule_key="defense_small"),
        )

    def test_combat_prediction_parses_into_a_rule_table_effect(self):
        self.assertEqual(
            parse_effect("combat_prediction:武感"),
            RuleTableEffect(rule_key="武感"),
        )

    @covers_requirement("skill-effect-model::passive-trait-effects-are-declared-inert-by-design-not-by-omission")
    def test_passive_trait_parses_into_a_flavor_effect(self):
        self.assertEqual(
            parse_effect("passive_trait:elf_longevity"),
            FlavorEffect(name="elf_longevity"),
        )

    def test_movement_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("movement:flight"),
            MovementEffect(mode="flight"),
        )
        self.assertEqual(
            parse_effect("movement:flash_step"),
            MovementEffect(mode="flash_step"),
        )

    def test_movement_rejects_unrecognized_modes(self):
        for effect in ("movement:swim", "movement:teleport", "movement:fly"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_weapon_style_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("weapon_style:dual_wield"),
            WeaponStyleEffect(style="dual_wield"),
        )

    def test_divine_mystery_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("divine_mystery:時間加速"),
            DivineMysteryEffect(name="時間加速", mechanized=False),
        )

    def test_confer_skill_partial_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("confer_skill_partial"), ConferralEffect())

    def test_set_disguise_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("set_disguise"), DisguiseEffect())

    def test_buff_apply_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("buff_apply:focus"),
            BuffApplyEffect(buff_key="focus"),
        )

    def test_self_buff_apply_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("self_buff_apply:focus"),
            SelfBuffApplyEffect(buff_key="focus"),
        )

    def test_confer_growth_rate_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("confer_growth_rate"), ConferGrowthRateEffect())

    def test_sexual_event_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("sexual_event:交合"),
            SexualEventEffect(event_name="交合"),
        )

    def test_damage_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("damage:fire:physical"),
            DamageEffect(element="fire", school="physical"),
        )

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_heal_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("heal:single"),
            HealEffect(shape="single"),
        )
        self.assertEqual(
            parse_effect("heal:area"),
            HealEffect(shape="area"),
        )

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_self_heal_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("self_heal"), SelfHealEffect())

    def test_malformed_heal_payload_raises(self):
        for effect in ("heal", "heal:allies", "self_heal:single", "self_heal:area"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_disengage_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("disengage:self"),
            DisengageEffect(mode="self"),
        )

    def test_cleanse_status_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("cleanse:status"),
            CleanseEffect(scope="status"),
        )

    def test_malformed_cleanse_raises(self):
        for effect in ("cleanse", "cleanse:status:extra", "cleanse:banana"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_unknown_prefix_raises(self):
        with self.assertRaises(ValueError):
            parse_effect("definitely_not_a_real_prefix:x")

    def test_malformed_stat_multiply_raises(self):
        for effect in (
            "stat_multiply:atk_phys",
            "stat_multiply:atk_phys:not-a-number",
            "stat_multiply:atk_phys:nan",
        ):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_malformed_damage_raises(self):
        for effect in ("damage", "damage:fire", "damage:fire:physical:extra"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_bare_prefixes_reject_a_payload(self):
        for effect in (
            "sexual_magic_mastery:extra",
            "confer_skill_partial:extra",
            "set_disguise:extra",
            "confer_growth_rate:extra",
        ):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_single_arg_prefixes_reject_embedded_colons(self):
        for effect in (
            "element_mastery_rank:主宰:extra",
            "passive_buff:a:b",
            "movement:a:b",
            "sexual_event:a:b",
        ):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_effect_dataclasses_are_frozen(self):
        effect = parse_effect("stat_multiply:atk_phys:100")
        with self.assertRaises(Exception):
            effect.trait = "defense"

    @covers_requirement("skill-effect-model::passive-trait-effects-are-declared-inert-by-design-not-by-omission")
    def test_no_rules_consumer_reads_flavor_effect(self):
        from pathlib import Path

        for relative in (
            "world/rules/combat.py",
            "world/rules/progression.py",
            "world/rules/combat_modifiers.py",
        ):
            path = Path(__file__).parents[3] / relative
            self.assertNotIn("FlavorEffect", path.read_text(encoding="utf-8"))
