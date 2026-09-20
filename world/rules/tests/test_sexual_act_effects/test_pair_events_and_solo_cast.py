"""Slice of ``test_sexual_act_effects``: PairEventNameTests, MonsterPairEventTests, ActPairEventHandlerTests, SoloActCastTests.
"""
from tools.spec_traceability import covers_requirement
import ast
import inspect
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.sexual_vocab import GENERIC_BODY_PART
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_SURFACES,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
    _handle_target_sexual_event,
)
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    load_effects_config,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)
from world.rules.pleasure import apply_pleasure_gain
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState
from world.rules.sexual_resist import ResistVerdict
from world.rules.targeting import RoomActionContext
from world.skills.registry import TargetSpec
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)
from .._combat_session_helpers import _live_registry, _race_key
# The YAML field vocabulary of the effects config, resolved through the
# config dataclass at import (the loader owns the names; this module never
# spells a shipped field name as a literal).
import dataclasses as _dc


from ._support import (
    _ActCastTestCase,
    _pair_act,
)


class PairEventNameTests(unittest.TestCase):
    """The pair_event_name selector implements the full D-12 table."""

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_opposite_sex_pair_resolves_first_vaginal_penetration(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        target = SimpleNamespace(sex="male")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "first_vaginal_penetration",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_both_female_pair_resolves_the_lesbian_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        target = SimpleNamespace(sex="female")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "penetrative_sex_with_female",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_both_male_pair_resolves_the_gay_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="male")
        target = SimpleNamespace(sex="male")
        self.assertEqual(
            pair_event_name(actor, [target], act),
            "penetrative_sex_with_male",
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_other_or_unknown_party_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="male"),
                [SimpleNamespace(sex="other")],
                act,
            )
        )
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(),
                [SimpleNamespace()],
                act,
            )
        )
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="female"),
                [SimpleNamespace(sex="unknown")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_pair_not_in_the_table_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex="female"),
                [SimpleNamespace(sex="other")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_single_participant_surviving_cast_resolves_no_event(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(SimpleNamespace(sex="female"), [], act)
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_none_sex_value_reads_as_the_unknown_default(self):
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex=None),
                [SimpleNamespace(sex="male")],
                act,
            )
        )

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_corrupted_non_string_sex_value_reads_as_the_unknown_default(self):
        # A corrupted non-SEX_VALUES attribute can never crash the pair sort:
        # it normalizes to the unknown default, which matches no pair.
        act = _pair_act()
        self.assertIsNone(
            pair_event_name(
                SimpleNamespace(sex=123),
                [SimpleNamespace(sex="male")],
                act,
            )
        )


class MonsterPairEventTests(EvenniaTestCase):
    """A Monster target reads sex as the default, resolving no pair event."""

    def setUp(self):
        super().setUp()
        self.monster = create_object(Monster, key="pair monster")

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_monster_target_resolves_no_event(self):
        act = _pair_act()
        actor = SimpleNamespace(sex="female")
        self.assertIsNone(pair_event_name(actor, [self.monster], act))
        self.assertEqual(self.monster.sex, "other")


class ActPairEventHandlerTests(_ActCastTestCase):
    """The act_pair_event:<key> handler through the full cast pipeline."""

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_opposite_sex_cast_applies_the_event_to_every_participant(self):
        skill, act = self._build_pair_act()
        self.actor.sex = "female"
        self.target.sex = "male"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.actor.sexual.virgin)
        self.assertFalse(self.target.sexual.virgin)
        self.assertIn("陰道性交", self.actor.sexual.experience_types)
        self.assertIn("陰道性交", self.target.sexual.experience_types)

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_other_unknown_party_stages_no_effect(self):
        skill, act = self._build_pair_act()
        self.actor.sex = "male"
        self.target.sex = "other"
        with self._install(skill, act)[0]:
            pending = _handle_act_pair_event(
                self.actor,
                [self.target],
                f"act_pair_event:{act.key}",
                {},
                1.0,
            )
        self.assertEqual(pending, [])

    @covers_requirement("sexual-act-effects::the-pair-event-handler-resolves-one-sex-conditional-event-per-cast-and-applies-it-to-every-participant")
    def test_absent_act_rejects_with_effect_resolution_failed(self):
        with self.assertRaises(Exception) as caught:
            _handle_act_pair_event(
                self.actor,
                [self.target],
                "act_pair_event:never_registered",
                {},
                1.0,
            )
        self.assertEqual(caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertIn(
            "act_pair_event:never_registered",
            str(caught.exception.detail),
        )


class SoloActCastTests(_ActCastTestCase):
    """A SELF-target solo act casts and gains pleasure through the pipeline."""

    def test_solo_act_casts_and_applies_pleasure_to_the_actor(self):
        (skill, act), = _act_family(
            "獨處線",
            (
                "test_solo_act",
                "測試自慰行為",
                "僅存在於測試中的合成自慰行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                1.0,
                ("masturbation_count",),
                (),
                (),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 10)
            self.assertEqual(self.actor.sexual.masturbation_count, 1)
