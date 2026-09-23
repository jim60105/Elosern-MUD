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
    RevealDisguiseEffect,
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
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec
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
            parse_effect("growth_rate:practice:5:wind"),
            GrowthRateEffect(stat="practice", multiplier=5.0, scope="wind"),
        )

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_unscoped_or_malformed_growth_rate_payloads_fail_closed(self):
        # A growth rate must name its tree: the old three-segment form no
        # longer parses and therefore fails registry load.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:practice:100")
        # The retired 'magic' stat key stays closed on the four-segment form.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:magic:5:wind")
        # The scope must be an ELEMENT_REGISTRY key.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:practice:5:notanelement")
        # The multiplier must be non-negative.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:practice:-1:wind")
        # The multiplier must be finite.
        for multiplier in ("nan", "inf"):
            with self.subTest(multiplier=multiplier):
                with self.assertRaises(ValueError):
                    parse_effect(f"growth_rate:practice:{multiplier}:wind")
        # Exactly four segments: a fifth segment is not a valid payload.
        with self.assertRaises(ValueError):
            parse_effect("growth_rate:practice:5:wind:extra")

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

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_bare_reveal_prefix_parses_into_its_marker_dataclass(self):
        self.assertEqual(parse_effect("reveal_disguise"), RevealDisguiseEffect())

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_retired_true_name_payload_fails_at_parse(self):
        # The payload-carrying grammar is retired entirely: this world admits
        # exactly one grade of veil, so there is no strength left to select.
        with self.assertRaises(ValueError):
            parse_effect("reveal_disguise:true_name")

    @covers_requirement("skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass")
    def test_unknown_reveal_payload_fails_at_parse(self):
        for effect in (
            "reveal_disguise:",
            "reveal_disguise:everything",
            "reveal_disguise:true_name:extra",
            "reveal_disguise:mundane",
        ):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

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

    @covers_requirement(
        "skill-effect-model::the-damage-effect-s-school-segment-is-validated-at-parse"
    )
    def test_damage_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("damage:fire:physical"),
            DamageEffect(element="fire", school="physical"),
        )
        self.assertEqual(
            parse_effect("damage:fire:magic"),
            DamageEffect(element="fire", school="magic"),
        )
        self.assertEqual(
            parse_effect("damage:none:physical"),
            DamageEffect(element=None, school="physical"),
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
        self.assertEqual(
            parse_effect("self_heal"),
            SelfHealEffect(basis="stat", fraction=None),
        )
        self.assertEqual(
            parse_effect("self_heal:missing_fraction:0.1"),
            SelfHealEffect(basis="missing_fraction", fraction=0.1),
        )
        self.assertEqual(
            parse_effect("self_heal:missing_fraction:1.0"),
            SelfHealEffect(basis="missing_fraction", fraction=1.0),
        )
        with self.assertRaises(ValueError):
            parse_effect("self_heal:")

    def test_malformed_heal_payload_raises(self):
        for effect in (
            "heal",
            "heal:allies",
            "self_heal:single",
            "self_heal:area",
            "self_heal:missing_fraction",
            "self_heal:missing_fraction:0",
            "self_heal:missing_fraction:1.5",
            "self_heal:missing_fraction:-0.1",
            "self_heal:missing_fraction:abc",
            "self_heal:missing_fraction:nan",
            "self_heal:missing_fraction:inf",
            "self_heal:missing_fraction:0.1:extra",
        ):
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

    @covers_requirement(
        "skill-effect-model::the-damage-effect-s-school-segment-is-validated-at-parse"
    )
    def test_malformed_damage_raises(self):
        for effect in (
            "damage",
            "damage:fire",
            "damage:fire:physical:extra",
            "damage:fire:sonic",
        ):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    @covers_requirement(
        "skill-effect-model::skilldef---post-init---rejects-unparseable-effects-at-construction"
    )
    def test_damage_skill_with_an_invalid_school_fails_at_construction(self):
        # The school membership check lives in parse_effect, so a declaration
        # carrying an out-of-set school fails when the SkillDef parses its
        # effects — registry-load time, not first cast.
        with self.assertRaises(ValueError):
            SkillDef(
                key="t_school_reject",
                label="合成校驗",
                description="宣稱封閉集合外 school 段的合成定義。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:sonic"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                group=None,
            )

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

        for relative, recursive in (
            ("world/rules/combat/battlefield.py", False),
            ("world/rules/combat/damage.py", False),
            ("world/rules/combat/healing.py", False),
            ("world/rules/combat/rounds.py", False),
            ("world/rules/progression", True),
            ("world/rules/combat_modifiers.py", False),
        ):
            path = Path(__file__).parents[3] / relative
            sources = path.rglob("*.py") if recursive else [path]
            for source in sources:
                with self.subTest(source=relative):
                    self.assertNotIn("FlavorEffect", source.read_text(encoding="utf-8"))
