"""Slice of ``test_sexual_act_effects``: SexualEventReuseTests, TargetSexualEventChannelBoundaryTests, ActorSexualEventHandlerTests.
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


class SexualEventReuseTests(_ActCastTestCase):
    """sexual_event:<name> entries reuse the existing handler; recipient scope
    follows the effect prefix statically — no name-based exception table."""

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table")
    def test_declared_event_calls_apply_event_for_every_participant(self):
        skill, act = self._build_duo_act(sexual_events=("frequent_stimulation",))
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(
                act.key,
                [self.target],
                {"sexual": {"part": "私處"}},
            )
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.target.sexual.sensitivity["私處"].level, "高")
            self.assertEqual(self.actor.sexual.sensitivity["私處"].level, "高")

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table")
    def test_no_new_handler_is_registered_for_sexual_event(self):
        self.assertIs(_EFFECT_HANDLERS["sexual_event"], _handle_sexual_event)
        # The target-scoped channel is the only dispatch-table addition, and it
        # is a distinct handler — the participant handler carries no scope fork.
        self.assertIs(
            _EFFECT_HANDLERS["sexual_event_target"], _handle_target_sexual_event
        )
        # The general apply_event route can mutate traits for rulebook events
        # beyond sexual state (post-review fix): the target channel declares
        # the same restoration surface as the participant channel, or a future
        # traits-mutating target row would roll back incompletely.
        self.assertEqual(
            _EFFECT_HANDLER_SURFACES["sexual_event_target"],
            _EFFECT_HANDLER_SURFACES["sexual_event"],
        )

    @covers_requirement("sexual-act-effects::sexual-event-target-name-applies-the-named-event-to-the-resolved-targets-only")
    def test_target_prefixed_stimulus_event_fires_on_targets_only(self):
        # The divine_sexual_arts cast semantics, carried by the prefix: the
        # acting entity is never a recipient of its own target-scoped event,
        # so the divine-arts exemption from self-pleasure (D-9) holds without
        # any name-based recipient table.
        pending = _handle_target_sexual_event(
            self.actor,
            [self.target],
            "sexual_event_target:stimulus_applied",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        self.assertIs(pending[0].entity, self.target)

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table")
    def test_the_participant_channel_no_longer_special_cases_stimulus(self):
        # The exception table is dead: the same event name through the
        # participant prefix now reaches every participant — scope is decided
        # by the prefix alone, never by the name.
        pending = _handle_sexual_event(
            self.actor,
            [self.target],
            "sexual_event:stimulus_applied",
            {},
            1.0,
        )
        entities = {effect.entity for effect in pending}
        self.assertEqual(entities, {self.actor, self.target})

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-resolve-through-the-participant-scoped-handler-with-no-name-based-exception-table")
    def test_self_act_event_reaches_the_actor_exactly_once(self):
        (skill, act), = _act_family(
            "獨處線",
            (
                "test_event_solo",
                "測試事件自慰",
                "僅存在於測試中的合成事件自慰行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                1.0,
                ("masturbation_count",),
                (),
                ("masturbation_climax",),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [])
        self.assertEqual(result.outcome, "success")
        self.assertIn("自慰", self.actor.sexual.experience_types)


class TargetSexualEventChannelBoundaryTests(_ActCastTestCase):
    """The sexual_event_target: channel's edges: full resist, AREA fan-out."""

    def _build_target_event_act(self, key: str = "test_target_event"):
        # A resistible synthetic duo act whose only effect is the target
        # channel — the divine_sexual_arts shape without naming the shipped
        # key (the shipped row itself is exercised in the divine catalog
        # module's cast tests).
        skill, act = self._build_duo_act(key, sexual_events=())
        skill = replace(skill, effects=["sexual_event_target:stimulus_applied"])
        return skill, act

    def _verdict(self, resisted: bool) -> ResistVerdict:
        return ResistVerdict(
            resisted=resisted,
            auto_comply=not resisted,
            roll=None if not resisted else 99,
            actor_score=1.0,
            resister_score=2.0,
        )

    @covers_requirement("sexual-act-effects::sexual-event-target-name-applies-the-named-event-to-the-resolved-targets-only")
    def test_sole_target_resisted_cast_succeeds_with_no_event_fired(self):
        # The resist gate excludes the target before effect resolution, so
        # the target-scoped handler stages nothing: an ordinary success with
        # no event, no RejectedAction, and no target state change.
        skill, act = self._build_target_event_act()
        with (
            self._install(skill, act)[0],
            self._install(skill, act)[1],
            patch(
                "world.rules.sexual_resist.resist_verdict",
                return_value=self._verdict(True),
            ),
            patch("world.rules.sexual_transitions.apply_event") as apply_spy,
        ):
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        apply_spy.assert_not_called()
        self.assertEqual(self.target.sexual.pleasure.base, 0)

    @covers_requirement("sexual-act-effects::sexual-event-target-name-applies-the-named-event-to-the-resolved-targets-only")
    def test_handler_stages_one_effect_per_non_actor_target(self):
        # The hypothetical AREA shape: a resolved target list carrying three
        # non-actor entities plus the actor itself stages exactly three
        # effects, and applying each routes apply_event to that target only.
        extras = [
            create_object(
                PlayerCharacter, key=f"act-extra-{index}", location=self.room1
            )
            for index in range(2)
        ]
        targets = [self.target, *extras, self.actor]
        with patch("world.rules.sexual_transitions.apply_event") as apply_spy:
            pending = _handle_target_sexual_event(
                self.actor, targets, "sexual_event_target:stimulus_applied", {}, 1.0
            )
            self.assertEqual(len(pending), 3)
            self.assertNotIn(self.actor, [effect.entity for effect in pending])
            for effect in pending:
                effect.apply()
        self.assertEqual(apply_spy.call_count, 3)
        recipients = [call.args[0] for call in apply_spy.call_args_list]
        self.assertEqual(recipients, [self.target, *extras])
        self.assertNotIn(self.actor, recipients)


class ActorSexualEventHandlerTests(_ActCastTestCase):
    """The sexual_event_actor:<name> handler and its observer gating."""

    def _build_self_act(
        self,
        key: str = "test_actor_event",
        *,
        actor_counters: tuple[str, ...] = ("exposure_act_count",),
        sexual_events: tuple[str, ...] = ("self_exposure",),
    ):
        (skill, act), = _act_family(
            "羞恥",
            (
                key,
                "測試演出行為",
                "僅存在於測試中的合成自我演出行為。",
                TargetSpec.SELF,
                {},
                10,
                None,
                None,
                1.0,
                actor_counters,
                (),
                sexual_events,
                False,
            ),
        )
        return skill, act

    def _cast_self_in(self, act_key: str, room):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                [],
                RoomActionContext(room, {}),
            )
        )

    @covers_requirement("sexual-act-effects::sexual-event-actor-name-applies-the-named-event-to-the-actor-only")
    def test_actor_scoped_event_reaches_the_actor_and_never_a_target(self):
        skill, act = self._build_duo_act(sexual_events=("self_exposure",))
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.target.sexual.exposure.value, 0)

    @covers_requirement("sexual-act-effects::sexual-event-actor-name-applies-the-named-event-to-the-actor-only")
    def test_area_self_exposure_lands_on_the_performer_not_the_audience(self):
        (skill, act), = _act_family(
            "羞恥",
            (
                "test_area_self_exposure",
                "測試群體演出",
                "僅存在於測試中的合成群體演出行為。",
                TargetSpec.AREA,
                {},
                10,
                None,
                "腰腹",
                0.5,
                (),
                (),
                ("self_exposure",),
                True,
            ),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast(act.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.target.sexual.exposure.value, 0)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_unobserved_cast_skips_the_watched_event_but_stages_the_others(self):
        alone = create_object(Room, key="actor event alone room")
        self.actor.location = alone
        skill, act = self._build_self_act(
            actor_counters=("watched_count", "exposure_act_count"),
            sexual_events=("self_exposure", "watched_during_activity"),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, alone)
        self.assertEqual(result.outcome, "success")
        self.assertNotIn("被觀看", self.actor.sexual.experience_types)
        self.assertEqual(self.actor.sexual.watched_count, 0)
        self.assertEqual(self.actor.sexual.exposure.value, 1)
        self.assertEqual(self.actor.sexual.exposure_act_count, 1)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_observed_cast_fires_the_watched_event(self):
        skill, act = self._build_self_act(
            actor_counters=("watched_count",),
            sexual_events=("watched_during_activity",),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, self.room1)
        self.assertEqual(result.outcome, "success")
        self.assertIn("被觀看", self.actor.sexual.experience_types)
        self.assertEqual(self.actor.sexual.watched_count, 1)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_unobserved_cast_skips_the_watched_counter_while_staging_others(self):
        alone = create_object(Room, key="counter alone room")
        self.actor.location = alone
        skill, act = self._build_self_act(
            actor_counters=("watched_count", "exposure_act_count"),
            sexual_events=(),
        )
        with self._install(skill, act)[0], self._install(skill, act)[1]:
            result = self._cast_self_in(act.key, alone)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.watched_count, 0)
        self.assertEqual(self.actor.sexual.exposure_act_count, 1)
