"""Slice of ``test_sexual_act_effects``: PleasureHandlerIntegrationTests, SexualCounterHandlerTests, MissingActRejectionTests.
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
)


class PleasureHandlerIntegrationTests(_ActCastTestCase):
    """The pleasure:<act_key> handler through the full cast pipeline."""

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_every_participant_gains_their_own_computed_pleasure(self):
        skill, act = self._build_duo_act(base_pleasure=20)
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 11)
            self.assertEqual(self.target.sexual.pleasure.base, 22)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_actor_uses_actor_part_and_target_uses_target_part(self):
        skill, act = self._build_duo_act(actor_part="腰腹", target_part="私處")
        self.actor.sexual.sensitivity["腰腹"] = "高"
        self.target.sexual.sensitivity["私處"] = "普通"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.pleasure.base, 15)
            self.assertEqual(self.target.sexual.pleasure.base, 22)

    @covers_requirement("sexual-act-effects::the-pleasure-effect-handler-resolves-each-participant-s-part-and-ratio-by-role-applies-gain-and-stages-a-climax-extension-when-a-進行中-participant-s-computed-gain-meets-threshold")
    def test_qualifying_gain_on_in_progress_target_stages_an_extension(self):
        skill, act = self._build_duo_act(base_pleasure=30)
        self.target.sexual.pleasure.base = 95
        self.target.sexual.climax_phase.value = "進行中"
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.target.sexual.pleasure.base, 100)
            self.assertEqual(self.target.sexual.pending_climax_extension, 1)

    def test_cast_stages_one_pending_effect_per_participant(self):
        skill, act = self._build_duo_act()
        with self._install(skill, act)[0]:
            pending = _handle_pleasure_effect(
                self.actor, [self.target], f"pleasure:{act.key}", {}, 1.0
            )
        self.assertEqual(len(pending), 2)
        self.assertIn(self.actor, [effect.entity for effect in pending])
        self.assertIn(self.target, [effect.entity for effect in pending])


class SexualCounterHandlerTests(_ActCastTestCase):
    """The sexual_counter:<act_key> role split (design D-7)."""

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_actor_only_counter_increments_once_on_the_actor_only(self):
        skill, act = self._build_duo_act(
            actor_counters=("restraint_count",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.restraint_count, 1)
            self.assertEqual(self.target.sexual.restraint_count, 0)

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_symmetric_counter_increments_on_both_sides(self):
        skill, act = self._build_duo_act()
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.actor.sexual.duo_act_count, 1)
            self.assertEqual(self.target.sexual.duo_act_count, 1)

    @covers_requirement("sexual-act-effects::the-counter-effect-handler-increments-actor-counters-on-the-actor-and-participant-counters-on-every-other-participant")
    def test_area_act_applies_participant_counters_to_every_other_participant(self):
        allies = []
        for index in range(3):
            ally = create_object(
                PlayerCharacter,
                key=f"act-ally-{index}",
                location=self.room1,
            )
            ally.race = _race_key()
            ally.apply_race_baseline()
            allies.append(ally)
        (skill, act), = _act_family(
            "關係",
            (
                "test_area_act",
                "測試群體行為",
                "僅存在於測試中的合成群體行為。",
                TargetSpec.AREA,
                {},
                10,
                "腰腹",
                "私處",
                0.5,
                (),
                ("group_act_count",),
                (),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, allies)
            self.assertEqual(result.outcome, "success")
            for ally in allies:
                self.assertEqual(ally.sexual.group_act_count, 1)
            self.assertEqual(self.actor.sexual.group_act_count, 0)

    def test_unknown_counter_name_rejects_the_action(self):
        skill, act = self._build_duo_act(
            actor_counters=("not_a_counter",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "rejected")

    def test_rejected_cast_leaves_no_state_or_sensitivity_trait_behind(self):
        skill, act = self._build_duo_act(
            actor_counters=("not_a_counter",),
            participant_counters=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
            self.assertEqual(result.outcome, "rejected")
        for entity in (self.actor, self.target):
            self.assertEqual(entity.sexual.pleasure.base, 0)
            self.assertEqual(entity.sexual.duo_act_count, 0)
            self.assertEqual(
                list(entity.sexual.sensitivity.items()),
                [],
                "a rejected cast must not leave a lazily-created sensitivity trait",
            )


class MissingActRejectionTests(_ActCastTestCase):
    """Both handlers reject an act key absent from the registry (defensive)."""

    def test_pleasure_handler_rejects_an_absent_act_key(self):
        with self.assertRaises(Exception) as caught:
            _handle_pleasure_effect(
                self.actor, [self.target], "pleasure:never_registered", {}, 1.0
            )
        self.assertEqual(
            caught.exception.detail,
            "pleasure:never_registered names an act absent from SEXUAL_ACT_REGISTRY",
        )

    def test_counter_handler_rejects_an_absent_act_key(self):
        with self.assertRaises(Exception) as caught:
            _handle_sexual_counter_effect(
                self.actor, [self.target], "sexual_counter:never_registered", {}, 1.0
            )
        self.assertEqual(
            caught.exception.detail,
            "sexual_counter:never_registered names an act absent from SEXUAL_ACT_REGISTRY",
        )
