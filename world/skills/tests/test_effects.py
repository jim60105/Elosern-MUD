"""Unit tests for the typed skill effect parser."""

from tools.spec_traceability import covers_requirement

import unittest

from world.skills.effects import (
    ActorSexualEventEffect,
    BuffApplyEffect,
    CleanseEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DamageEffect,
    DisengageEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    FlavorEffect,
    GrowthRateEffect,
    HealEffect,
    MovementEffect,
    PleasureEffect,
    RuleTableEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualCounterEffect,
    SexualEventEffect,
    SexualMasteryEffect,
    StatMultiplyEffect,
    TargetSexualEventEffect,
    WeaponStyleEffect,
    parse_effect,
)
# Synthetic payloads for payload-agnostic parser arms. Each branch accepts any
# single argument, so an invented key (kit t_* convention) exercises the
# identical parse path without naming shipped content.
_FLAVOR_TRAIT = "t_longevity"
_EVENT_NAME = "t_hush_rite"


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
            parse_effect("growth_rate:practice:100"),
            GrowthRateEffect(stat="practice", multiplier=100.0),
        )
        # The retired 'magic' stat key fails closed at parse time.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:magic:100")

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_retired_element_mastery_rank_prefix_fails_closed(self):
        # The cast gate retired with the magic-XP engine; the prefix left
        # the recognized set and fails closed at parse (and registry load).
        with self.assertRaises(ValueError):
            parse_effect("element_mastery_rank:t_synth_name")

    def test_sexual_magic_mastery_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("sexual_magic_mastery"), SexualMasteryEffect())

    def test_passive_buff_parses_into_a_rule_table_effect(self):
        self.assertEqual(
            parse_effect("passive_buff:t_rule_key"),
            RuleTableEffect(rule_key="t_rule_key"),
        )

    def test_combat_prediction_parses_into_a_rule_table_effect(self):
        self.assertEqual(
            parse_effect("combat_prediction:t_feel_key"),
            RuleTableEffect(rule_key="t_feel_key"),
        )

    @covers_requirement("skill-effect-model::passive-trait-effects-are-declared-inert-by-design-not-by-omission")
    def test_passive_trait_parses_into_a_flavor_effect(self):
        self.assertEqual(
            parse_effect(f"passive_trait:{_FLAVOR_TRAIT}"),
            FlavorEffect(name=_FLAVOR_TRAIT),
        )

    def test_movement_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("movement:flight"),
            MovementEffect(mode="flight"),
        )
        # The closed movement vocabulary's other accepted mode is shipped
        # grammar with no synthetic substitute; its positive parse assertion
        # lives in the registered skill-registry content contract.

    def test_movement_rejects_unrecognized_modes(self):
        for effect in ("movement:swim", "movement:teleport", "movement:fly"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_weapon_style_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("weapon_style:t_synth_style"),
            WeaponStyleEffect(style="t_synth_style"),
        )

    def test_divine_mystery_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("divine_mystery:t_time_name"),
            DivineMysteryEffect(name="t_time_name", mechanized=False),
        )

    def test_confer_skill_partial_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("confer_skill_partial"), ConferralEffect())

    def test_set_disguise_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("set_disguise"), DisguiseEffect())

    def test_buff_apply_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("buff_apply:t_buff_key"),
            BuffApplyEffect(buff_key="t_buff_key"),
        )

    def test_self_buff_apply_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("self_buff_apply:t_buff_key"),
            SelfBuffApplyEffect(buff_key="t_buff_key"),
        )

    def test_confer_growth_rate_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("confer_growth_rate"), ConferGrowthRateEffect())

    def test_sexual_event_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect(f"sexual_event:{_EVENT_NAME}"),
            SexualEventEffect(event_name=_EVENT_NAME),
        )

    def test_sexual_event_actor_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("sexual_event_actor:t_actor_event"),
            ActorSexualEventEffect(event_name="t_actor_event"),
        )

    def test_sexual_event_actor_rejects_missing_or_double_payload(self):
        for effect in ("sexual_event_actor", "sexual_event_actor:a:b"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    def test_sexual_event_target_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("sexual_event_target:t_target_event"),
            TargetSexualEventEffect(event_name="t_target_event"),
        )

    def test_sexual_event_target_rejects_missing_or_double_payload(self):
        for effect in ("sexual_event_target:", "sexual_event_target:a:b"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    @covers_requirement("skill-effect-model::pleasure-and-sexual-counter-parse-into-bare-key-carrying-typed-dataclasses")
    def test_pleasure_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("pleasure:masturbation_seed"),
            PleasureEffect(act_key="masturbation_seed"),
        )

    @covers_requirement("skill-effect-model::pleasure-and-sexual-counter-parse-into-bare-key-carrying-typed-dataclasses")
    def test_sexual_counter_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("sexual_counter:masturbation_seed"),
            SexualCounterEffect(act_key="masturbation_seed"),
        )

    @covers_requirement("skill-effect-model::pleasure-and-sexual-counter-parse-into-bare-key-carrying-typed-dataclasses")
    def test_missing_act_key_raises_at_construction(self):
        for effect in ("pleasure:", "sexual_counter:"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

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
        # The bare prefix IS the whole shipped effect ID (closed vocabulary);
        # its positive parse assertion lives in the registered skill-registry
        # content contract. What remains here is the arity boundary.
        with self.assertRaises(ValueError):
            parse_effect("self_heal:")

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
