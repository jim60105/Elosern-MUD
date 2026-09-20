"""Slice of ``test_registry_structure``: ActFamilyTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules.rulebook.schema import load_rules
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.skills import handler
from world.skills.handler import SkillHandler
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
import world.skills.registry as registry_module
from world.skills import sexual_acts
import world.skills.sexual_acts._builder as _builder_module
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.effects import TargetSexualEventEffect
from world.skills.sexual_acts.divine import DIVINE_ACTS
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    _FORBIDDEN_SEXUAL_EVENTS,
    SexualActDef,
    _act_family,
)

from ._support import (
    _seed_act_row,
)

class ActFamilyTests(unittest.TestCase):
    """The _act_family() pairing contract and its five per-row checks."""

    @covers_requirement("sexual-act-registry::every-sexualactdef-is-paired-with-an-ordinary-skilldef-under-the-same-key-categorised-sexual-act")
    def test_row_produces_a_matching_skilldef_and_sexualactdef(self):
        skill, act = _seed_act_row("test_act")
        self.assertIs(skill.category, SkillCategory.SEXUAL_ACT)
        self.assertEqual(skill.key, "test_act")
        self.assertEqual(act.key, "test_act")
        self.assertEqual(act.unlock, {})

    @covers_requirement("sexual-act-registry::every-sexualactdef-is-paired-with-an-ordinary-skilldef-under-the-same-key-categorised-sexual-act")
    def test_sex_act_costs_no_resource_and_casts_out_of_combat(self):
        skill, _ = _seed_act_row()
        self.assertEqual(skill.cost, {})
        self.assertTrue(skill.usable_out_of_combat)
        self.assertIs(skill.kind, SkillKind.ACTIVE)

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_zero_actor_pleasure_ratio_is_rejected_for_a_non_divine_family(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_ratio", actor_pleasure_ratio=0.0)
        self.assertIn("bad_ratio", str(caught.exception))

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_zero_actor_pleasure_ratio_is_accepted_for_a_divine_family(self):
        skill, act = _seed_act_row(
            "divine_row",
            actor_pleasure_ratio=0.0,
            requires_divine_arts=True,
        )
        self.assertTrue(skill.requires_divine_arts)
        self.assertEqual(act.actor_pleasure_ratio, 0.0)

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_non_finite_actor_pleasure_ratio_is_rejected_for_every_family(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(ratio=bad):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row("bad_finite_ratio", actor_pleasure_ratio=bad)
                self.assertIn("bad_finite_ratio", str(caught.exception))
            with self.subTest(ratio=bad, divine=True):
                with self.assertRaises(ValueError):
                    _seed_act_row(
                        "bad_finite_ratio_divine",
                        actor_pleasure_ratio=bad,
                        requires_divine_arts=True,
                    )

    def test_non_integer_unlock_threshold_is_rejected(self):
        for bad in (True, 1.5, "1"):
            with self.subTest(threshold=bad):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row("bad_threshold", unlock={"restraint_count": bad})
                self.assertIn("bad_threshold", str(caught.exception))

    def test_non_mapping_unlock_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_unlock_shape", unlock=("restraint_count", 1))
        self.assertIn("bad_unlock_shape", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_declaring_the_generic_body_part_is_rejected(self):
        for part_field in ("actor_part", "target_part"):
            with self.subTest(part_field=part_field):
                kwargs = {"actor_part": "私處", "target_part": None}
                kwargs[part_field] = GENERIC_BODY_PART
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row(f"bad_part_{part_field}", **kwargs)
                self.assertIn(f"bad_part_{part_field}", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_interspecies_act_declaring_a_target_part_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_interspecies", line="異種", target_part="私處")
        self.assertIn("bad_interspecies", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_divine_act_declaring_a_target_part_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row(
                "bad_divine",
                line="神之秘法",
                target_part="私處",
                requires_divine_arts=True,
            )
        self.assertIn("bad_divine", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_part_outside_body_parts_is_rejected_naming_key_and_part(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_body_part", actor_part="觸手")
        message = str(caught.exception)
        self.assertIn("bad_body_part", message)
        self.assertIn("觸手", message)

    def test_non_positive_base_pleasure_is_rejected(self):
        for bad in (0, -5, 1.5):
            with self.subTest(base_pleasure=bad):
                with self.assertRaises(ValueError):
                    _seed_act_row("bad_pleasure", base_pleasure=bad)

    def test_non_bare_bool_resistible_is_rejected(self):
        with self.assertRaises(ValueError):
            _seed_act_row("bad_resistible", resistible=1)

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_row_effects_carry_both_new_prefixes_keyed_to_its_own_act(self):
        skill, _ = _seed_act_row("test_act")
        self.assertEqual(
            skill.effects,
            ["pleasure:test_act", "sexual_counter:test_act"],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_declared_sexual_events_gain_one_entry_per_name_in_order(self):
        # A name in the actor-scoped vocabulary (watched_during_activity) is
        # emitted through the sexual_event_actor: prefix; a participant-scoped
        # name keeps the plain sexual_event: prefix.
        skill, _ = _seed_act_row(
            "test_act",
            sexual_events=("frequent_stimulation", "watched_during_activity"),
        )
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "sexual_event:frequent_stimulation",
                "sexual_event_actor:watched_during_activity",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_pair_events_row_gains_exactly_one_trailing_act_pair_event_entry(self):
        skill, _ = _seed_act_row(
            "test_act",
            target_spec=TargetSpec.SINGLE,
            pair_events=((("female", "male"), "first_vaginal_penetration"),),
        )
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "act_pair_event:test_act",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_plain_row_never_gains_an_act_pair_event_entry(self):
        skill, _ = _seed_act_row("test_act", sexual_events=("frequent_stimulation",))
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "sexual_event:frequent_stimulation",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_multiple_rows_each_name_only_their_own_key(self):
        rows = (
            (
                "first_act",
                "第一行為",
                "測試用第一行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                0.5,
                (),
                (),
                (),
                True,
            ),
            (
                "second_act",
                "第二行為",
                "測試用第二行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                0.5,
                (),
                (),
                (),
                True,
            ),
        )
        pairs = _act_family("獨處線", *rows)
        self.assertEqual(len(pairs), 2)
        for skill, act in pairs:
            for effect in skill.effects:
                if effect.startswith("pleasure:") or effect.startswith("sexual_counter:"):
                    self.assertEqual(
                        effect.partition(":")[2],
                        act.key,
                        f"{skill.key!r} names another act's key in {effect!r}",
                    )

    @covers_requirement("sexual-act-registry::an-act-s-sexual-events-never-names-a-pleasure-wetness-or-climax-settlement-owned-event")
    def test_forbidden_event_fails_at_construction_naming_key_and_event(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_event_act", sexual_events=("stimulus_applied",))
        message = str(caught.exception)
        self.assertIn("bad_event_act", message)
        self.assertIn("stimulus_applied", message)

    @covers_requirement("sexual-act-registry::an-act-s-sexual-events-never-names-a-pleasure-wetness-or-climax-settlement-owned-event")
    def test_direct_stimulus_applied_is_permitted(self):
        skill, _ = _seed_act_row(
            "ok_event_act",
            sexual_events=("direct_stimulus_applied",),
        )
        self.assertIn("sexual_event:direct_stimulus_applied", skill.effects)

    def test_every_forbidden_event_name_is_rejected(self):
        for event in (
            "stimulus_applied",
            "sustained_stimulus_applied",
            "extreme_stimulus_applied",
            "climax_ends",
            "climax_extended",
        ):
            with self.subTest(event=event):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row(f"bad_{event}", sexual_events=(event,))
                self.assertIn(f"bad_{event}", str(caught.exception))

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_row_length_guard_rejects_any_length_besides_13_or_14(self):
        base = (
            "len_act",
            "長度行為",
            "測試長度守衛的合成行為。",
            TargetSpec.SELF,
            {},
            10,
            "私處",
            None,
            0.5,
            (),
            (),
            (),
            True,
        )
        for row in (base[:12], (*base, (), ("extra",))):
            with self.subTest(length=len(row)):
                with self.assertRaises(ValueError) as caught:
                    _act_family("獨處線", row)
                self.assertIn("len_act", str(caught.exception))
