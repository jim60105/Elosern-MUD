from twisted.internet import defer
"""Tests for the epithet-nomination composition-root service.

Unit seams pin the fire-and-forget scheduling contract (never raises, never
blocks, no client consulted offline), rest-point gating (logout/rest/exam/quest
observers through ``transaction.on_commit``), the suppression short-circuit
(single ballot + decline cooldown, accept never cools down), persistence
delegated to the rules writer, and the bounded panel push.

The real-composition classes (change ``verify-recent-deed-settlement-flows``)
insert no narrative row: a real ACQUIRE purchase completion, a real adult
resolver settlement and a real multi-round encounter settle through their
owning writers, then selection, the rendered prompt, citation validation and
ballot persistence run unchanged. Only the external transport is a double;
it returns five bounded candidates citing the request's own rendered sources.
The committed-state probe lives in ``TitleNominationCommittedReloadTests``
(Django ``TransactionTestCase``) and is the only class that force-evicts the
idmapper caches. No single test calls a live model or network service.
"""

import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from django.test import TransactionTestCase, override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from server import title_nomination_service as service
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.title_nomination import register_title_nomination
from world.lore.sexual_vocab import BODY_PARTS
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.narrative.events import get_committed_award_results, record_narrative_event
from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.observability import transcript
from world.quests import runtime as quest_runtime
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    quest,
    register,
)
from world.rules import guild_exams
from world.rules import titles as title_rules
from world.rules.action import ActionRequest, ActionResolver
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    read_session,
    reconstruct_battlefield,
    settle_session,
    submit_player_action,
)
from world.rules.economy import buy
from world.rules.tests._combat_session_helpers import (
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.targeting import RoomActionContext
from world.skills.effects import EffectPolicy
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.skills.sexual_acts import SexualActDef
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_SHOPS,
    SYNTH_STARTER_EPITHET,
    make_skill,
)


def _profiles(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _quest_receipt(entity, quest_id="q1", awards=()):
    """The canonical receipt the quest-transition writer hands the observer."""
    from world.quests.runtime import QuestCompletionReceipt

    return QuestCompletionReceipt(
        source_id=f"quest:{quest_id}:completion:{entity.pk}",
        actor=entity,
        actor_id=int(entity.pk),
        quest_id=quest_id,
        definition_key="dk1",
        issuer_key="npc:test_commission",
        objective={"kind": "defeat", "quantity": 1, "stage_index": 0,
                   "destination_room_id": None, "bound_identities": []},
        awards=tuple(awards),
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _reply(candidates):
    return json.dumps({"candidates": list(candidates)}, ensure_ascii=False)


def _good_client():
    client = FakeLLMClient()
    client.add_response(
        lambda descriptor: True,
        _reply(
            [
                {"display": "火焰之心", "basis": "焚盡匪寨", "source_ids": ["quest:test_001"]},
                {"display": "破曉之刃", "basis": "曙間退敵", "source_ids": ["quest:test_001"]},
                {"display": "沉默守望", "basis": "夜守村口", "source_ids": ["quest:test_001"]},
                {"display": "荒野行者", "basis": "穿林三日", "source_ids": ["quest:test_001"]},
                {"display": "月影之舞", "basis": "月下退賊", "source_ids": ["quest:test_001"]},
            ]
        ),
    )
    return client


def _void_client():
    """A client whose round produces no candidate and therefore no ballot."""
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, _reply([]))
    return client


# The real-composition fixture's own synthetic rows: one ACQUIRE quest and one
# adult act. Nothing here names a shipped quest, item or act.
_H_QUEST_KEY = "t_h_real_deed_quest"
_T_BOUGHT = SYNTH_ITEMS["t_ember_spray"].key
_H_DEED = "t_h_completed_deed"
_H_DEED_PAIR = "t_h_completed_deed_pair"
_H_ADULT_DEED = "t_h_adult_deed"

_H_ADULT_ACT = SexualActDef(
    key="t_h_adult_act",
    unlock={},
    base_pleasure=15,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.8,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=("first_vaginal_penetration",),
    resistible=False,
)
_H_ADULT_SKILL = make_skill(
    key="t_h_adult_act",
    label="t_提交行為",
    description="t_合成成人行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    category=SkillCategory.SEXUAL_ACT,
    usable_out_of_combat=True,
    effects=[
        f"pleasure:{_H_ADULT_ACT.key}",
        f"sexual_counter:{_H_ADULT_ACT.key}",
        "sexual_event:first_vaginal_penetration",
    ],
)
_H_HEAL_SKILL = make_skill(
    "t_h_heal_deed",
    element="light",
    effects=("heal:single",),
    effect_policies=(EffectPolicy(coefficient=1.0),),
)


def _quest_title_rows() -> dict:
    """Synthetic quest-completed rows plus one adult counter row."""
    rows = {
        key: FixedTitleDef(
            key=key,
            display_name_zh=display,
            category=TitleCategory.EXPLORE,
            flavor_zh="你把那樁委託收在身後。",
            hint_zh="完成指定的具名委託即可獲得。",
            predicate=TitlePredicate(
                family=TitlePredicateFamily.QUEST_COMPLETED,
                quest_key=_H_QUEST_KEY,
            ),
        )
        for key, display in ((_H_DEED, "委託留名"), (_H_DEED_PAIR, "委託雙名"))
    }
    rows[_H_ADULT_DEED] = FixedTitleDef(
        key=_H_ADULT_DEED,
        display_name_zh="親密留痕",
        category=TitleCategory.ROMANCE,
        flavor_zh="那一次接觸留在了身上。",
        hint_zh="完成指定的成人行為計數即可獲得。",
        predicate=TitlePredicate(
            family=TitlePredicateFamily.COUNTER_THRESHOLD,
            counter="duo_act_count",
            threshold=1,
        ),
    )
    return rows


_RECENT_DEEDS_MARKER = "近期事件紀錄（JSON；可能為空）："


def _rendered_deed_groups(descriptor):
    """Return the recent-deed groups exactly as the rendered request carries them."""
    content = descriptor.messages[-1]["content"]
    line = next(
        (row for row in content.splitlines() if row.startswith(_RECENT_DEEDS_MARKER)),
        None,
    )
    if line is None:
        return ()
    payload = json.loads(line[len(_RECENT_DEEDS_MARKER):])
    return tuple(payload.get("recent_deeds", ()))


def _rendered_source_ids(descriptor) -> tuple[str, ...]:
    """The source ids present in the request's own rendered material."""
    seen: list[str] = []
    for group in _rendered_deed_groups(descriptor):
        for source_id in group.get("source_ids", ()):
            if source_id not in seen:
                seen.append(source_id)
    return tuple(seen)


def _request_citing_candidates(descriptor) -> list[dict]:
    """Five bounded candidates whose citations come from the rendered request.

    The middle candidates prove the deterministic filters still run on real
    material: one fails the display form rule and one cites an ID the request
    never rendered. The last candidate cites the whole supplied set, at but not
    past the request's own bound.
    """
    source_ids = _rendered_source_ids(descriptor)
    first, last = source_ids[0], source_ids[-1]
    return [
        {"display": "平寇先鋒", "basis": "完成真正的委託交付", "source_ids": [first]},
        {"display": "柔情守護", "basis": "與同行者完成一次成人行為", "source_ids": [last]},
        {"display": "bad-form", "basis": "ASCII 形式不合格", "source_ids": [first]},
        {
            "display": "寨破之晨",
            "basis": "引用了未渲染的來源",
            "source_ids": ["occurrence:hand:not-rendered"],
        },
        {"display": "信義之伴", "basis": "引用這一輪的完整來源", "source_ids": list(source_ids)},
    ]


class _RequestCitingTransport:
    """Fake external transport only: it cites the request's rendered sources."""

    def __init__(self) -> None:
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        # A malformed read here is a real fixture failure and must surface.
        return defer.succeed(_reply(_request_citing_candidates(descriptor)))


class _PendingTransport(_RequestCitingTransport):
    """A transport that holds its response until the test releases it."""

    def __init__(self) -> None:
        super().__init__()
        self._pending = defer.Deferred()

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self._pending

    def release(self):
        """Answer the pending round with the captured request's own citations."""
        candidates = _request_citing_candidates(self.calls[-1])
        self._pending.callback(_reply(candidates))
        return candidates


class _NoPush:
    """Patch target recorder for the bounded panel push."""

    def __init__(self):
        self.calls = []

    def __call__(self, entity, watchers):
        self.calls.append((entity, watchers))


class NominationSchedulingTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        # The first-claim grant banks whatever the starter seam holds; patch
        # the shared synthetic declaration so a collision candidate can match
        # the banked display without pinning the shipped spelling.
        starter_seam = patch(
            "world.lore.titles.STARTER_EPITHET", SYNTH_STARTER_EPITHET
        )
        starter_seam.start()
        self.addCleanup(starter_seam.stop)
        # The test runner does not boot the server hooks; install the layer
        # registration the same way at_server_start does (idempotent).
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="nominee")
        self.push = _NoPush()
        self.push_patcher = patch.object(service, "_push_ballot_panel", self.push)
        self.push_patcher.start()
        self.addCleanup(self.push_patcher.stop)
        # Seed an authorized recent deed so the player has eligible material by default
        record_narrative_event(
            source_id="quest:test_001",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock", return_value=self.clock
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_happy_path_persists_and_pushes(self):
        deferred = self._schedule(_good_client(), watchers=(("session", "epoch"),))
        self.assertIsNotNone(deferred)
        self.assertEqual(
            title_rules.safe_pending_ballot(self.player),
            (
                {"display": "火焰之心", "basis": "焚盡匪寨"},
                {"display": "破曉之刃", "basis": "曙間退敵"},
                {"display": "沉默守望", "basis": "夜守村口"},
            ),
        )
        self.assertEqual(self.push.calls, [(self.player, (("session", "epoch"),))])

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_pending_ballot_suppresses_without_touching_transport(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "先來", "basis": "一"}]
            )
        )
        client = _good_client()
        self.assertIsNone(self._schedule(client))
        self.assertEqual(client.calls, [])
        self.assertEqual(
            title_rules.safe_pending_ballot(self.player),
            ({"display": "先來", "basis": "一"},),
        )

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_decline_cooldown_suppresses_then_expires(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "甲名", "basis": "一"}]
            )
        )
        title_rules.decline_epithet_ballot(self.player)
        client = _good_client()
        self.assertIsNone(self._schedule(client))
        self.assertEqual(client.calls, [])
        # Past the second day boundary the same trigger fires again.
        day = title_rules._DAY_SECONDS
        clock = SimpleNamespace(tick=10 * day)
        with patch("world.rules.titles.ballot.get_world_clock", return_value=clock):
            self.assertIsNotNone(self._schedule(_good_client()))

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_decline_digest_flows_into_the_prompt(self):
        # The durable decline log is the prompt's soft-learning feed: the
        # declined displays must appear in the next round's user message.
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "已拒之名", "basis": "一"}]
            )
        )
        title_rules.decline_epithet_ballot(self.player)
        client = _good_client()
        clock = SimpleNamespace(tick=10 * title_rules._DAY_SECONDS)
        with patch("world.rules.titles.ballot.get_world_clock", return_value=clock):
            self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("已拒之名", user_text)

    @covers_requirement("title-system::nomination-prompts-contain-authorized-structured-deeds-and-advisory-identity")
    def test_adult_action_structured_outcome_survives_into_prompt(self):
        # Record an authorized adult deed with field_access, actor, recipients and outcomes
        # along with a private/forbidden field on another participant
        player_pk = str(self.player.pk)
        record_narrative_event(
            source_id="adult:committed_act_001",
            event_type="adult_action",
            content={
                "location": {"id": "", "label": ""},
                "act_key": "synth_touch",
                "act_name": "撫觸測試",
                "player_id": player_pk,
                "actor": {"id": player_pk, "name": "nominee"},
                "recipients": [{"id": "npc_partner", "name": "花語者", "private_feeling": "forbidden_secret_value"}],
                "outcomes": {
                    # One committed settled effect in the admitted shape; an
                    # unsupported effect row fails the whole record closed.
                    "effects": [
                        {
                            "kind": "pleasure_gain",
                            "actor_id": player_pk,
                            "target_id": "npc_partner",
                            "target_name": "花語者",
                            "result": {"amount": 12},
                        }
                    ],
                },
                "field_access": {
                    player_pk: ["actor", "recipients", "physical_effects"],
                },
            },
            participants=[player_pk, "npc_partner"],
            tick=100,
        )
        # Record an unauthorized narrative event (player is not a participant)
        record_narrative_event(
            source_id="adult:unauthorized_act_999",
            event_type="adult_action",
            content={"location": {"id": "", "label": ""}, "act_key": "secret", "outcome": "unauthorized_outcome"},
            participants=["other_person_1", "other_person_2"],
            tick=100,
        )
        client = _good_client()
        self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("adult:committed_act_001", user_text)
        self.assertIn("synth_touch", user_text)
        self.assertIn("花語者", user_text)
        # Verify unauthorized event and private forbidden fields never enter the prompt
        self.assertNotIn("unauthorized_outcome", user_text)
        self.assertNotIn("forbidden_secret_value", user_text)

    def test_removal_digest_flows_into_the_prompt(self):
        # The durable removal log is the second soft-learning feed: the
        # removed display must appear in the next round's user message.
        title_rules.bank_epithet(self.player, "苔徑新客", "初次走入苔徑。", 1)
        title_rules.bank_epithet(self.player, "放下之名", "舊事蹟。", 2)
        title_rules.remove_epithet(self.player, "放下之名")
        client = _good_client()
        self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("放下之名", user_text)

    def test_push_passes_the_captured_epoch(self):
        # The unpatched push path hands publish_panel_update the epoch
        # captured at trigger time (the coordinator's own guard test pins
        # the mismatch behavior; this pins the wiring). Suspend the
        # class-level push stub first.
        self.push_patcher.stop()
        self.addCleanup(self.push_patcher.start)
        from web.webclient.presentation.context import PresentationContext

        with (
            patch(
                "web.webclient.presentation.coordinator.publish_panel_update",
                return_value=None,
            ) as publish,
            patch(
                "web.webclient.presentation.ingress.build_presentation_context",
                return_value=PresentationContext(
                    actor=self.player, protocol_version=1
                ),
            ),
        ):
            service._push_ballot_panel(self.player, (("session", "epoch-7"),))
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(publish.call_args.kwargs["expected_epoch"], "epoch-7")
        self.assertEqual(publish.call_args.args[0], "session")

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_accept_never_starts_a_cooldown(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "甲名", "basis": "一"}]
            )
        )
        title_rules.accept_epithet(self.player, 1)
        self.assertIsNotNone(self._schedule(_good_client()))

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_disabled_profile_fires_nothing(self):
        client = _good_client()
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            deferred = service.schedule_epithet_nomination(self.player, client=client)
            if deferred is not None:
                await_result(deferred)
        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())
        self.assertEqual(client.calls, [])
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_offline_client_builder_yields_no_call(self):
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            self.assertIsNone(service.schedule_epithet_nomination(self.player))

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_empty_feed_skips_nomination(self):
        # Character with no recorded deeds produces no nomination attempt
        empty_player = create_object(PlayerCharacter, key="empty-nominee")
        client = _good_client()
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(empty_player, client=client)
        self.assertIsNone(deferred)
        self.assertEqual(client.calls, [])
        self.assertFalse(empty_player.attributes.has(title_rules.PENDING_BALLOT_KEY))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_nomination_diagnostics_preserve_privacy(self):
        with patch("server.title_nomination_service.log_info") as mock_info:
            deferred = self._schedule(_good_client(), trigger="wake")
            self.assertIsNotNone(deferred)
            admitted_calls = [
                call for call in mock_info.call_args_list
                if call.args and call.args[0] == "title_nomination_admitted"
            ]
            self.assertEqual(len(admitted_calls), 1)
            ctx = admitted_calls[0].kwargs.get("context", {})
            self.assertEqual(ctx.get("player"), str(self.player.pk))
            self.assertEqual(ctx.get("trigger"), "wake")
            # The admitted tick is the frozen one, never zero or a later read.
            self.assertEqual(ctx.get("frozen_tick"), 100)
            self.assertEqual(ctx.get("source_count"), 1)
            # Ensure full private deed prose is not in logging context
            for val in ctx.values():
                self.assertNotIn("completed_objective", str(val))

    @covers_requirement("title-system::the-nomination-pipeline-is-5-candidates-through-schema-and-collision-filters")
    def test_void_rounds_store_nothing(self):
        cases = ["{not json", _reply([{"display": "甲名", "basis": "一", "source_ids": ["quest:test_001"]}])]
        for text in cases:
            with self.subTest(text=text[:16]):
                client = FakeLLMClient()
                client.add_response(lambda descriptor: True, text)
                self._schedule(client)
                self.assertFalse(
                    self.player.attributes.has(title_rules.PENDING_BALLOT_KEY)
                )

    @covers_requirement("title-system::the-nomination-pipeline-is-5-candidates-through-schema-and-collision-filters")
    def test_all_filtered_candidates_store_nothing(self):
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: True,
            _reply([{"display": SYNTH_STARTER_EPITHET.display, "basis": "撞名", "source_ids": ["quest:test_001"]}] * 5),
        )
        title_rules.award_first_quest_epithet(self.player, source_id="test:init:first_quest")
        self._schedule(client)
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))
        self.assertEqual(self.push.calls, [])

    def test_non_player_and_malformed_state_never_raise(self):
        npc = create_object(PlayerCharacter, key="nominee-2")
        npc.attributes.add(title_rules.TITLE_COLLECTION_KEY, "damaged")
        with override_settings(LLM_PROFILES=_profiles()):
            self.assertIsNone(
                service.schedule_epithet_nomination(None, client=_good_client())
            )
            self.assertIsNone(
                service.schedule_epithet_nomination(
                    "not-an-entity", client=_good_client()
                )
            )
            self.assertIsNone(
                service.schedule_epithet_nomination(npc, client=_good_client())
            )

    def test_synchronous_build_failure_is_swallowed(self):
        client = _good_client()
        with (
            override_settings(LLM_PROFILES=_profiles()),
            patch.object(
                service, "_build_context", side_effect=RuntimeError("boom")
            ),
        ):
            self.assertIsNone(
                service.schedule_epithet_nomination(self.player, client=client)
            )


class RestBoundaryTests(EvenniaTest):
    """Wake and qualifying quest boundaries trigger scheduling; midnight/exams do not."""

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="rest-nominee")
        record_narrative_event(
            source_id="quest:test_rest_nominee",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock", return_value=self.clock
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_wake_transition_triggers_scheduling(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                service.notify_wake_transition(self.player, occurrence_id="occ:wake:1")
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_live_combat_wake_is_ineligible(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            service.notify_wake_transition(self.player, occurrence_id="occ:wake:combat", in_combat=True)
            schedule.assert_not_called()

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_replaying_wake_transition_creates_no_second_attempt(self):
        with patch.object(service, "schedule_epithet_nomination", wraps=service.schedule_epithet_nomination) as schedule:
            # First wake runs
            d1 = service.schedule_epithet_nomination(self.player, occurrence_id="occ:wake:replay:1", client=_good_client())
            # Second replayed wake with same occurrence id must be ignored
            d2 = service.schedule_epithet_nomination(self.player, occurrence_id="occ:wake:replay:1", client=_good_client())
            self.assertIsNone(d2)

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_replayed_completion_notification_creates_no_second_attempt(self):
        # The occurrence identity is the committed completion's own source id;
        # replaying it after the in-flight slot cleared must still be inert.
        # The first round is deliberately void, so no pending ballot can stand
        # in for the occurrence guard being tested.
        source_id = _quest_receipt(self.player).source_id
        d1 = service.schedule_epithet_nomination(
            self.player, occurrence_id=source_id, source_id=source_id,
            client=_void_client(),
        )
        self.assertIsNotNone(d1)
        await_result(d1)
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)
        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())
        d2 = service.schedule_epithet_nomination(
            self.player, occurrence_id=source_id, source_id=source_id,
            client=_good_client(),
        )
        self.assertIsNone(d2)

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_overlapping_wake_and_logout_makes_one_call(self):
        record_narrative_event(
            source_id="quest:in_flight_test",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_in_flight", "definition_key": "dk", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        d_unblock = defer.Deferred()
        class BlockingClient:
            def get_response(self, descriptor):
                return d_unblock

        d1 = service.schedule_epithet_nomination(self.player, client=BlockingClient(), trigger="wake")
        self.assertIsNotNone(d1)
        # Concurrent logout while wake is in flight
        d2 = service.schedule_epithet_nomination(self.player, client=_good_client(), trigger="logout")
        self.assertIsNone(d2)

        # Release blocking client
        d_unblock.callback(_reply([{"display": "火焰之心", "basis": "焚盡匪寨", "source_ids": ["quest:test_001"]}]))
        await_result(d1)
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_all_failure_paths_release_in_flight_slot(self):
        player_id = str(self.player.pk)

        # 1. Transport error
        client_err = FakeLLMClient()
        client_err.add_timeout(lambda d: True)
        d_err = service.schedule_epithet_nomination(self.player, client=client_err)
        if d_err is not None:
            await_result(d_err)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)

        # 2. Disabled profile
        with override_settings(LLM_PROFILES=_profiles(title_nomination={"enabled": False})):
            d_dis = service.schedule_epithet_nomination(self.player)
            self.assertIsNone(d_dis)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)

        # 3. Empty feed
        empty_p = create_object(PlayerCharacter, key="empty-release")
        d_empty = service.schedule_epithet_nomination(empty_p, client=_good_client())
        self.assertIsNone(d_empty)
        self.assertNotIn(str(empty_p.pk), service._IN_FLIGHT_PLAYERS)

        # 4. Void output (empty candidates survivor list)
        client_void = FakeLLMClient()
        client_void.add_response(lambda d: True, "{not valid json")
        d_void = service.schedule_epithet_nomination(self.player, client=client_void)
        if d_void is not None:
            await_result(d_void)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)


    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_restart_retains_ballots_without_generation_resumption(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "存檔稱號", "basis": "持久化"}]
            )
        )
        # Simulate restart
        service.reset_nomination_triggers_for_tests()
        self.assertEqual(len(service._IN_FLIGHT_PLAYERS), 0)
        # Ballot is still intact
        self.assertEqual(title_rules.safe_pending_ballot(self.player)[0]["display"], "存檔稱號")


    @covers_requirement("title-system::immediate-source-suppression-uses-automatic-award-results")
    def test_immediate_source_award_suppression(self):
        from world.rules.titles.awards import AutomaticTitleAward
        player_pk = str(self.player.pk)
        record_narrative_event(
            source_id="quest:award_occ",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_award", "definition_key": "dk", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        award_for_player = AutomaticTitleAward(
            source_id="quest:award_occ",
            recipient_id=player_pk,
            kind="fixed",
            title_id="test_title",
            granted_tick=100,
            display_name="測試稱號",
        )
        award_for_other = AutomaticTitleAward(
            source_id="quest:award_occ",
            recipient_id="99999",
            kind="fixed",
            title_id="test_title",
            granted_tick=100,
            display_name="他人稱號",
        )

        # Award for another does not suppress
        res_other = self._schedule(
            _good_client(),
            source_id="quest:award_occ",
            award_results=(award_for_other,),
        )
        self.assertIsNotNone(res_other)
        service._IN_FLIGHT_PLAYERS.clear()

        # Award for player suppresses immediately
        res_player = service.schedule_epithet_nomination(
            self.player,
            client=_good_client(),
            source_id="quest:award_occ",
            award_results=(award_for_player,),
        )
        self.assertIsNone(res_player)


class ObserverWiringTests(EvenniaTest):
    """Wake/quest observers schedule only after the settlement commits."""

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="observed-nominee")
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    def test_registration_is_idempotent_and_observers_are_installed(self):
        saved_quest = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        from world.rules import fatigue as fatigue_rules
        saved_wake = list(fatigue_rules._WAKE_TRANSITION_OBSERVERS)
        self.addCleanup(
            lambda: (
                fatigue_rules._WAKE_TRANSITION_OBSERVERS.__setitem__(slice(None), saved_wake),
                quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                    slice(None), saved_quest
                ),
            )
        )
        service._TRIGGERS_REGISTERED = False
        service.register_nomination_triggers()
        service.register_nomination_triggers()
        self.assertEqual(
            fatigue_rules._WAKE_TRANSITION_OBSERVERS.count(service.notify_wake_transition), 1
        )
        self.assertEqual(
            quest_runtime._QUEST_COMPLETION_OBSERVERS.count(
                service._on_quest_completion
            ),
            1,
        )

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_observers_defer_to_on_commit(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with transaction.atomic():
                with self.captureOnCommitCallbacks(execute=False):
                    service.notify_wake_transition(self.player, occurrence_id="occ:wake:commit")
                    service._on_quest_completion(_quest_receipt(self.player))
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                service.notify_wake_transition(self.player, occurrence_id="occ:wake:commit2")
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_rolled_back_transactions_schedule_nothing(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service.notify_wake_transition(self.player, occurrence_id="occ:wake:rollback")
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service._on_quest_completion(_quest_receipt(self.player))
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_owner_receipt_supplies_the_canonical_identity_and_envelope(self):
        # The service never rebuilds the source identity or re-reads the award
        # envelope: it forwards exactly what the quest-transition owner
        # committed, and reuses that identity as the occurrence key so a
        # replayed receipt admits no second attempt.
        receipt = _quest_receipt(self.player, quest_id="q_forward", awards=("awarded",))
        with patch.object(service, "_schedule_after_commit") as schedule:
            service._on_quest_completion(receipt)
        schedule.assert_called_once_with(
            self.player,
            source_id="quest:q_forward:completion:%s" % self.player.pk,
            award_results=("awarded",),
            occurrence_id="quest:q_forward:completion:%s" % self.player.pk,
            trigger="quest_completion",
        )


class _RealDeedFixture:
    """Real composition fixture: purchase completion plus adult resolver settlement.

    Every entity is built through normal Evennia construction, and both deeds
    reach the durable store through their owning production writers. The
    fixture never inserts a narrative row, never patches selection, prompt
    construction, citation validation or ballot persistence, and uses no live
    model or network transport.
    """

    award_titles = False
    frozen_tick = 50_000

    def setUp(self):
        extra = {"titles": _quest_title_rows()} if self.award_titles else None
        open_synthetic_scope(
            self, "items", "prices", "shops", "titles", extra=extra
        )
        super().setUp()
        register_catalog()
        register_title_nomination()
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)
        self.clock = SimpleNamespace(tick=self.frozen_tick)
        clock_patcher = patch(
            "server.title_nomination_service.read_world_clock",
            return_value=self.clock,
        )
        clock_patcher.start()
        self.addCleanup(clock_patcher.stop)
        push_patcher = patch.object(
            service, "_push_ballot_panel", lambda *args: None
        )
        push_patcher.start()
        self.addCleanup(push_patcher.stop)

        shop_key = next(iter(SYNTH_SHOPS))
        offer = synth_offer_rule(_T_BOUGHT, max_stock=20)
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    shop_key: synth_shop_config(
                        shop_key, (_T_BOUGHT,), offer_rules=(offer,)
                    )
                }
            ),
        )
        self.room = create_object(Room, key="h-real-room")
        self.merchant = create_object(
            NPC, key="h-real-keeper", location=self.room
        )
        component = Merchant.create(
            self.merchant, service_id="h_real_merchant", shop_key=shop_key
        )
        self.merchant.components.add(component)
        component.merchant_stock = {_T_BOUGHT: 20}
        self.player = create_object(
            PlayerCharacter, key="h-real-hero", location=self.room
        )
        self.player.db.wallet = 1000
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.target = create_object(
            PlayerCharacter, key="h-real-partner", location=self.room
        )
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.untouched = create_object(
            PlayerCharacter, key="h-real-untouched", location=self.room
        )
        self.unrelated = create_object(
            PlayerCharacter, key="h-real-unrelated", location=self.room
        )
        self.target.db.private_hidden = "h-target-private"
        self.untouched.db.private_hidden = "h-untouched-private"
        self.unrelated.db.private_hidden = "h-unrelated-private"
        self.definition = register(
            quest(
                _H_QUEST_KEY,
                stages=(QuestStage(0, acquire(_T_BOUGHT, quantity=1)),),
            )
        )
        self.record = accept(self.player, self.definition)
        self.source_id = (
            f"quest:{self.record.quest_id}:completion:{self.player.pk}"
        )

    # -- real gameplay owners ------------------------------------------------

    def _buy(self):
        with patch(
            "world.rules.economy.get_world_clock",
            return_value=WorldClock(12 * 3600),
        ):
            return buy(self.player, self.merchant, _T_BOUGHT, 1, self.player.pk)

    def _resolve_adult_act(self, *, target=None):
        target = self.target if target is None else target
        target.sexual.virgin = True
        self.player.db.skills = {
            "active": [_H_ADULT_SKILL.key],
            "passive": [],
        }
        request = ActionRequest(
            self.player,
            _H_ADULT_SKILL.key,
            [target],
            RoomActionContext(self.room),
        )
        with (
            patch.dict(
                "world.skills.registry.SKILL_REGISTRY",
                {_H_ADULT_SKILL.key: _H_ADULT_SKILL},
            ),
            patch.dict(
                "world.skills.sexual_acts.SEXUAL_ACT_REGISTRY",
                {_H_ADULT_ACT.key: _H_ADULT_ACT},
            ),
        ):
            return ActionResolver.resolve(request)

    def _resolve_heal(self):
        self.player.db.skills = {
            "active": [_H_HEAL_SKILL.key],
            "passive": [],
        }
        request = ActionRequest(
            self.player,
            _H_HEAL_SKILL.key,
            [self.target],
            RoomActionContext(self.room),
        )
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY",
            {_H_HEAL_SKILL.key: _H_HEAL_SKILL},
        ):
            return ActionResolver.resolve(request)

    def _settle_deeds(self):
        """Run both real settlements and return their committed occurrences."""
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        with self.captureOnCommitCallbacks(execute=True):
            self._buy()
        completion = NarrativeEvent.objects.get(source_id=self.source_id)
        self.assertEqual(completion.event_type, "quest_completion")
        self.assertEqual(completion.content["award_results"], [])

        # The untouched control's real gameplay state is captured before the
        # adult settlement so a mutation would be observable afterwards.
        self.untouched_before = (
            self.untouched.sexual.virgin,
            self.untouched.sexual.pleasure.value,
            frozenset(self.untouched.sexual.experience_types),
        )
        result = self._resolve_adult_act()
        self.assertEqual(result.outcome, "success", result)
        adult = NarrativeEvent.objects.get(event_type="adult_action")
        self.assertIn(str(self.player.pk), adult.participants)
        self.assertIn(str(self.target.pk), adult.participants)
        self.assertNotIn(str(self.untouched.pk), adult.participants)
        self.assertFalse(self.target.sexual.virgin)
        return completion, adult

    def _schedule(self, client, *, entity=None, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player if entity is None else entity,
                client=client,
                **kwargs,
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    def _nominate(self, transport):
        """Fire the committed wake trigger with the fake external transport."""
        with override_settings(LLM_PROFILES=_profiles()):
            with patch.object(
                service, "_build_nomination_client", return_value=transport
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    service.notify_wake_transition(
                        self.player, occurrence_id="occ:h:real:wake"
                    )
        return transport


class TitleNominationRealSettlementTests(
    _RealDeedFixture, QuestRegistryIsolation, EvenniaTest
):
    """The real owners settle first; the composition root reads what committed.

    These tests deliberately create no narrative event: the ACQUIRE purchase
    completion and the adult resolver are the producers. Selection, prompt
    rendering, citation validation and ballot persistence then run unchanged,
    with a transport that replaces only the external model call.
    """

    @covers_requirement(
        "title-system::recent-deed-eligibility-is-closed-and-personally-authorized",
        "title-system::quest-nomination-observes-the-committed-completion-owner",
        "title-system::candidate-citations-refer-only-to-actually-rendered-sources",
    )
    def test_real_settlements_reach_the_request_and_persist_a_ballot(self):
        completion, adult = self._settle_deeds()
        transport = self._nominate(_RequestCitingTransport())

        self.assertEqual(len(transport.calls), 1)
        requested = _rendered_source_ids(transport.calls[0])
        self.assertIn(completion.source_id, requested)
        self.assertIn(adult.source_id, requested)

        rendered = transport.calls[0].messages[-1]["content"]
        # Authorized facts survive prompt construction.
        self.assertIn(_H_ADULT_SKILL.key, rendered)
        self.assertIn(self.target.key, rendered)
        adult_groups = [
            group
            for group in _rendered_deed_groups(transport.calls[0])
            if group["group_type"] == "adult_action"
        ]
        self.assertEqual(len(adult_groups), 1)
        adult_facts = adult_groups[0]["facts"]
        self.assertEqual(
            adult_facts["actor"],
            {
                "id": str(self.player.pk),
                "name": self.player.key,
                "role": "actor",
            },
        )
        recipients = {
            row["id"]: row for row in adult_facts["recipients"]
        }
        self.assertEqual(
            recipients[str(self.target.pk)]["role"], "recipient"
        )
        self.assertNotIn(str(self.untouched.pk), recipients)
        effects = adult_facts["outcomes"]["effects"]
        self.assertTrue(
            any(
                row["kind"] == "pleasure_gain"
                and row["target_id"] == str(self.target.pk)
                and row["result"]["amount"] > 0
                for row in effects
            )
        )
        # The real recipient-state transition happened; the untouched
        # control's gameplay state is byte-identical.
        self.assertFalse(self.target.sexual.virgin)
        self.assertEqual(
            (
                self.untouched.sexual.virgin,
                self.untouched.sexual.pleasure.value,
                frozenset(self.untouched.sexual.experience_types),
            ),
            self.untouched_before,
        )
        # An unrelated character and every unprojected private field stay out.
        for private in (
            "h-target-private",
            "h-untouched-private",
            "h-unrelated-private",
            self.untouched.key,
            self.unrelated.key,
        ):
            self.assertNotIn(private, rendered)

        ballot = title_rules.safe_pending_ballot(self.player)
        self.assertEqual(
            [entry["display"] for entry in ballot],
            ["平寇先鋒", "柔情守護", "信義之伴"],
        )
        # The form-invalid and unknown-citation candidates were filtered out.
        self.assertNotIn(
            "bad-form", [entry["display"] for entry in ballot]
        )
        self.assertNotIn(
            "寨破之晨", [entry["display"] for entry in ballot]
        )
        self.assertNotIn(
            "平寇先鋒", title_rules.safe_full_title(self.player)
        )
        # The untouched control gains neither a ballot nor a title.
        self.assertEqual(
            title_rules.safe_pending_ballot(self.untouched), ()
        )
        self.assertEqual(title_rules.safe_full_title(self.untouched), "")

    @covers_requirement(
        "title-system::citation-provenance-stops-at-the-generation-boundary"
    )
    def test_real_flow_keeps_transcript_provenance_without_credentials(self):
        self._settle_deeds()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        client = _RequestCitingTransport()
        with (
            patch.object(
                transcript, "_transcript_dir", return_value=tmp.name
            ),
            patch.object(
                transcript, "_today", return_value=date(2026, 10, 22)
            ),
            override_settings(
                LLM_TRANSCRIPT_ENABLED=True,
                LLM_PROFILES=_profiles(
                    title_nomination={
                        "api_key": "sk-h-transcript-secret"
                    }
                ),
            ),
            patch.object(
                service, "_build_nomination_client", return_value=client
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            service.notify_wake_transition(
                self.player, occurrence_id="occ:h:transcript"
            )

        self.assertEqual(len(client.calls), 1)
        path = Path(tmp.name) / "2026-10-22.jsonl"
        self.assertTrue(path.exists())
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        # The fake replaces only the external transport, so the transport's
        # own exchange record is absent by construction; the guardrail outcome
        # is the record that carries the accepted final text.
        self.assertEqual({record["kind"] for record in records}, {"outcome"})
        outcome = records[0]
        self.assertEqual(outcome["result"], "ok")
        text = outcome["final_text"]
        for source_id in _rendered_source_ids(client.calls[0]):
            self.assertIn(source_id, text)
        self.assertNotIn("sk-h-transcript-secret", text)
        self.assertNotIn("h-target-private", text)

    @covers_requirement(
        "title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact"
    )
    def test_failed_rounds_leave_no_ballot_no_cooldown_and_gameplay_playable(self):
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        with self.captureOnCommitCallbacks(execute=True):
            self._buy()
        inventory_before = list(self.player.db.inventory or [])
        wallet_before = self.player.db.wallet

        # Empty material: a character with no committed deed and no transport.
        empty = create_object(PlayerCharacter, key="h-real-empty")
        empty_client = _RequestCitingTransport()
        self.assertIsNone(self._schedule(empty_client, entity=empty))
        self.assertEqual(empty_client.calls, [])

        # A disabled profile never reaches the transport.
        disabled_client = _RequestCitingTransport()
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            disabled = service.schedule_epithet_nomination(
                self.player, client=disabled_client
            )
            if disabled is not None:
                self.assertFalse(await_result(disabled))
        self.assertEqual(disabled_client.calls, [])

        # Transport failure voids the round.
        failing = FakeLLMClient()
        failing.add_timeout(lambda descriptor: True)
        self.assertIsNotNone(self._schedule(failing))
        self.assertEqual(len(failing.calls), 1)

        # Malformed output (four candidates) voids the round by shape.
        malformed = FakeLLMClient()
        malformed.add_response(
            lambda descriptor: True,
            _reply(
                [
                    {
                        "display": "夜色無聲",
                        "basis": "不足五筆的輸出",
                        "source_ids": [self.source_id],
                    }
                ]
                * 4
            ),
        )
        self.assertIsNotNone(self._schedule(malformed))

        for client in (empty_client, disabled_client, failing, malformed):
            self.assertFalse(
                self.player.attributes.has(title_rules.PENDING_BALLOT_KEY)
            )
            self.assertFalse(
                title_rules.nomination_suppressed(self.player, now_tick=0)
            )
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)
        # Gameplay itself is untouched: wallet and inventory are unchanged and
        # a real action still settles.
        self.assertEqual(list(self.player.db.inventory or []), inventory_before)
        self.assertEqual(self.player.db.wallet, wallet_before)
        self.target.traits.hp.current = 20
        heal = self._resolve_heal()
        self.assertEqual(heal.outcome, "success", heal)
        self.assertGreater(self.target.traits.hp.current, 20)


class TitleNominationLateResultTests(
    _RealDeedFixture, QuestRegistryIsolation, EvenniaTest
):
    """A valid late round is refused by the ballot/admission guard."""

    @covers_requirement(
        "title-system::nomination-has-one-in-flight-request-per-player-identity"
    )
    def test_valid_late_round_cannot_replace_a_ballot_and_releases_admission(self):
        self._settle_deeds()
        pending = _PendingTransport()
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=pending, trigger="wake"
            )
        self.assertIsNotNone(deferred)
        self.assertEqual(len(pending.calls), 1)
        requested = set(_rendered_source_ids(pending.calls[0]))

        # A second trigger while the first is in flight is refused by admission.
        overlapping = _RequestCitingTransport()
        with override_settings(LLM_PROFILES=_profiles()):
            self.assertIsNone(
                service.schedule_epithet_nomination(
                    self.player, client=overlapping, trigger="logout"
                )
            )
        self.assertEqual(overlapping.calls, [])

        # A ballot exists by the time the valid round arrives.
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player,
                [{"display": "先到之選", "basis": "較早落庫"}],
            )
        )

        candidates = pending.release()
        # The released round is shape-valid: exactly five bounded candidates
        # with at least the three survivors the request's sources support.
        self.assertEqual(len(candidates), 5)
        valid = [
            candidate
            for candidate in candidates
            if set(candidate["source_ids"]) <= requested
        ]
        self.assertGreaterEqual(len(valid), 3)

        self.assertFalse(await_result(deferred))
        self.assertEqual(
            title_rules.safe_pending_ballot(self.player),
            ({"display": "先到之選", "basis": "較早落庫"},),
        )
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)


class TitleNominationRollbackTests(
    _RealDeedFixture, QuestRegistryIsolation, EvenniaTest
):
    """Failures after real writes but before the owning commit restore everything."""

    award_titles = True

    @covers_requirement(
        "title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction",
        "title-system::award-evidence-finalizes-atomically-and-survives-replay",
    )
    def test_purchase_failure_after_the_nested_quest_writer_restores_every_surface(self):
        from world.quests import transitions as quest_transitions

        read_records(self.player)
        title_rules.read_title_state(self.player)
        real = quest_transitions._settle_quest_completion_events
        granted_inside = []

        def recording_settlement(actor, old_entries, completed):
            real(actor, old_entries, completed)
            granted_inside.append(title_rules.banked_fixed_keys(actor))

        with (
            patch(
                "world.quests.transitions._settle_quest_completion_events",
                side_effect=recording_settlement,
            ),
            patch(
                "world.rules.economy.materialize_registry_object",
                side_effect=RuntimeError("injected after the quest writer"),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError):
                self._buy()

        # The nested writer really granted the titles before the failure.
        self.assertTrue(granted_inside)
        self.assertIn(_H_DEED, granted_inside[0])
        # Drop the in-memory attribute cache so the assertions read the
        # persisted row rather than the writer's restored handler state.
        self.player.attributes.reset_cache()
        self.assertEqual(
            read_records(self.player)[0].state, QuestState.IN_PROGRESS
        )
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(self.player.db.wallet, 1000)
        self.assertEqual(
            title_rules.read_title_state(self.player),
            ([], {"fixed": None, "epithet": None}),
        )
        self.assertFalse(
            self.player.attributes.has(title_rules.TITLE_COLLECTION_KEY)
        )
        self.assertFalse(
            self.player.attributes.has(title_rules.TITLE_EQUIPPED_KEY)
        )
        self.assertIsNone(get_committed_award_results(self.source_id))
        self.assertFalse(
            NarrativeEvent.objects.filter(
                event_type="quest_completion"
            ).exists()
        )
        self.assertFalse(
            ProjectionProgress.objects.filter(
                source_id=self.source_id
            ).exists()
        )

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay",
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance",
    )
    def test_action_failure_after_evidence_writes_restores_gameplay_and_evidence(self):
        from world.narrative import action_adapters as adapter_module
        from world.rules.titles.planner import title_event_effect_planner

        self.target.sexual.virgin = True
        # A legal pre-existing counter satisfies the synthetic counter row, so
        # the real planner stages a real title grant on this action.
        self.player.sexual.record_duo_act()
        title_rules.read_title_state(self.player)
        player_pleasure = self.player.sexual.pleasure.value
        target_pleasure = self.target.sexual.pleasure.value
        real = adapter_module.record_action_settlement_evidence
        observed = {}

        def failing_record(request, *args, **kwargs):
            real(request, *args, **kwargs)
            observed["banked"] = title_rules.banked_fixed_keys(self.player)
            observed["event"] = NarrativeEvent.objects.get(
                source_id=request.source_id
            )
            raise RuntimeError("injected after action evidence")

        with (
            patch.dict(
                "world.rules.action.contracts._EVENT_EFFECT_PLANNERS",
                {"title": title_event_effect_planner},
            ),
            patch.object(
                adapter_module,
                "record_action_settlement_evidence",
                side_effect=failing_record,
            ),
        ):
            result = self._resolve_adult_act()

        # The real planner granted the fixed title and the evidence writer
        # recorded its award result inside the transaction the failure aborts.
        self.assertIn(_H_ADULT_DEED, observed["banked"])
        self.assertEqual(
            [
                row["title_id"]
                for row in observed["event"].content["award_results"]
            ],
            [_H_ADULT_DEED],
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertFalse(NarrativeEvent.objects.exists())
        self.assertFalse(ProjectionProgress.objects.exists())
        self.assertIsNone(
            get_committed_award_results(observed["event"].source_id)
        )
        self.assertEqual(title_rules.banked_fixed_keys(self.player), ())
        self.assertEqual(
            title_rules.read_title_state(self.player),
            ([], {"fixed": None, "epithet": None}),
        )
        self.assertTrue(self.target.sexual.virgin)
        self.assertEqual(
            self.player.sexual.pleasure.value, player_pleasure
        )
        self.assertEqual(
            self.target.sexual.pleasure.value, target_pleasure
        )


class TitleNominationNotificationReplayTests(
    _RealDeedFixture, QuestRegistryIsolation, EvenniaTest
):
    """A replayed committed receipt is inert; the gameplay owner is never rerun."""

    award_titles = True

    @covers_requirement(
        "title-system::award-evidence-finalizes-atomically-and-survives-replay",
        "title-system::quest-nomination-observes-the-committed-completion-owner",
    )
    def test_replayed_committed_receipt_creates_no_occurrence_and_keeps_awards(self):
        receipts = []
        saved = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        self.addCleanup(
            quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__,
            slice(None),
            saved,
        )
        quest_runtime._QUEST_COMPLETION_OBSERVERS[:] = [receipts.append]
        with self.captureOnCommitCallbacks(execute=True):
            self._buy()
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        source_id = receipt.source_id
        event_before = NarrativeEvent.objects.get(source_id=source_id)
        awards_before = get_committed_award_results(source_id)
        self.assertEqual(
            sorted(award.title_id for award in awards_before),
            [_H_DEED, _H_DEED_PAIR],
        )

        service.reset_nomination_triggers_for_tests()
        transport = _RequestCitingTransport()
        with (
            override_settings(LLM_PROFILES=_profiles()),
            patch.object(
                service, "_build_nomination_client", return_value=transport
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            service._on_quest_completion(receipt)
        self.assertIn(source_id, service._PROCESSED_OCCURRENCES)
        processed = set(service._PROCESSED_OCCURRENCES)

        # Replay only the committed notification. With the award check
        # neutered, the occurrence identity is the only remaining guard.
        with (
            override_settings(LLM_PROFILES=_profiles()),
            patch.object(
                service, "_build_nomination_client", return_value=transport
            ),
            patch.object(
                service, "_check_source_award_suppression", return_value=False
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            service._on_quest_completion(receipt)

        self.assertEqual(service._PROCESSED_OCCURRENCES, processed)
        self.assertEqual(transport.calls, [])
        self.assertEqual(
            NarrativeEvent.objects.filter(source_id=source_id).count(), 1
        )
        self.assertEqual(
            NarrativeEvent.objects.get(
                source_id=source_id
            ).content["award_results"],
            event_before.content["award_results"],
        )
        self.assertEqual(
            sorted(
                award.title_id
                for award in get_committed_award_results(source_id)
            ),
            sorted(award.title_id for award in awards_before),
        )


class TitleNominationCombatCompositionTests(
    QuestRegistryIsolation, BattlefieldIsolation, EvenniaTest
):
    """Repeated real combat rounds reach the request as one encounter group."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "items",
            "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        register_title_nomination()
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)
        clock_patcher = patch(
            "server.title_nomination_service.read_world_clock",
            return_value=SimpleNamespace(tick=50_000),
        )
        clock_patcher.start()
        self.addCleanup(clock_patcher.stop)
        push_patcher = patch.object(
            service, "_push_ballot_panel", lambda *args: None
        )
        push_patcher.start()
        self.addCleanup(push_patcher.stop)
        self.room = create_object(Room, key="h-combat-room")
        self.player = _player("h-combat-hero")
        self.player.location = self.room
        self.monster = _monster("h-combat-foe", hp=500, atk=1)
        self.monster.location = self.room

    @covers_requirement(
        "title-system::encounter-grouping-uses-unique-occurrence-identity",
        "title-system::recent-deed-groups-retain-outcomes-and-stable-provenance",
    )
    def test_repeated_rounds_and_terminal_outcome_keep_the_encounter_group(self):
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        engage(self.player, self.monster)
        with (
            patch(
                "world.rules.combat.battlefield.roll_d100", return_value=50
            ),
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.rounds.roll_d100", return_value=50),
        ):
            for _ in range(2):
                result = submit_player_action(
                    self.player, BASIC_ATTACK_KEY, [self.monster]
                )
                self.assertEqual(result["outcome"], "round", result)

        actions = list(
            NarrativeEvent.objects.filter(
                event_type="skill_use",
                content__actor__id=str(self.player.pk),
            ).order_by("source_id")
        )
        self.assertEqual(len(actions), 2)
        current = read_session(self.player)
        settle_session(
            self.player,
            current,
            reconstruct_battlefield(self.player, current),
            "victory",
        )

        transport = _RequestCitingTransport()
        with override_settings(LLM_PROFILES=_profiles()):
            with patch.object(
                service, "_build_nomination_client", return_value=transport
            ):
                with self.captureOnCommitCallbacks(execute=True):
                    service.notify_wake_transition(
                        self.player, occurrence_id="occ:h:combat"
                    )

        self.assertEqual(len(transport.calls), 1)
        groups = _rendered_deed_groups(transport.calls[0])
        combat_groups = [
            group
            for group in groups
            if group["group_type"] == "combat_encounter"
        ]
        self.assertEqual(len(combat_groups), 1)
        group = combat_groups[0]
        facts = group["facts"]
        self.assertEqual(facts["encounter_id"], current.engagement_id)
        self.assertEqual(facts["outcome"], "victory")
        own_summaries = [
            summary
            for summary in facts["actions"]
            if summary["facts"]["actor"]["id"] == str(self.player.pk)
        ]
        self.assertEqual(
            sum(summary["count"] for summary in own_summaries), 2
        )
        self.assertTrue(
            {event.source_id for event in actions}
            <= set(group["source_ids"])
        )

        ballot = title_rules.safe_pending_ballot(self.player)
        self.assertEqual(
            [entry["display"] for entry in ballot],
            ["平寇先鋒", "柔情守護", "信義之伴"],
        )


class TitleNominationCommittedReloadTests(
    _RealDeedFixture, QuestRegistryIsolation, TransactionTestCase
):
    """A committed ballot and its title grants read back from fresh instances.

    ``TransactionTestCase`` (the ``EquipmentGrowthCommittedReloadTests`` and
    ``DurableRoundAdmissionTests`` precedent) is the documented exception here:
    the probe exists to observe committed state, so the reads cannot be served
    by the writing instance. Both the ``ObjectDB`` and ``Attribute`` idmapper
    caches are force-evicted before a fresh typeclass instance is loaded.
    """

    award_titles = True

    def _reread(self, entity):
        from evennia.objects.models import ObjectDB
        from evennia.typeclasses.attributes import Attribute

        entity.save()
        for model in (ObjectDB, Attribute):
            model.flush_instance_cache(force=True)
        fresh = PlayerCharacter.objects.get(pk=entity.pk)
        self.assertIsNot(fresh, entity)
        return fresh

    @covers_requirement(
        "title-system::the-ballot-persists-unchanged-until-consent",
        "title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only",
        "title-system::award-evidence-finalizes-atomically-and-survives-replay",
    )
    def test_committed_ballot_and_grants_survive_a_fresh_instance(self):
        self._buy()
        completion = NarrativeEvent.objects.get(source_id=self.source_id)
        awards_before = get_committed_award_results(self.source_id)
        self.assertEqual(
            sorted(award.title_id for award in awards_before),
            [_H_DEED, _H_DEED_PAIR],
        )
        self.assertIn(
            _H_DEED, title_rules.banked_fixed_keys(self.player)
        )

        transport = _RequestCitingTransport()
        with override_settings(LLM_PROFILES=_profiles()):
            with patch.object(
                service, "_build_nomination_client", return_value=transport
            ):
                service.notify_wake_transition(
                    self.player, occurrence_id="occ:h:reload"
                )
        self.assertEqual(len(transport.calls), 1)
        ballot_before = title_rules.safe_pending_ballot(self.player)
        self.assertEqual(len(ballot_before), 3)
        state_before = title_rules.read_title_state(self.player)

        fresh = self._reread(self.player)
        self.assertEqual(
            title_rules.safe_pending_ballot(fresh), ballot_before
        )
        self.assertEqual(
            title_rules.read_title_state(fresh), state_before
        )
        self.assertEqual(
            sorted(title_rules.banked_fixed_keys(fresh)),
            [_H_DEED, _H_DEED_PAIR],
        )
        self.assertEqual(
            sorted(award.title_id for award in get_committed_award_results(self.source_id)),
            sorted(award.title_id for award in awards_before),
        )
        self.assertEqual(
            NarrativeEvent.objects.get(
                source_id=self.source_id
            ).content["award_results"],
            completion.content["award_results"],
        )


class FrozenAdmissionTickTests(EvenniaTest):
    """The admitted world tick is frozen once and reused by every diagnostic."""

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="frozen-tick-nominee")
        push_patcher = patch.object(service, "_push_ballot_panel", lambda *args: None)
        push_patcher.start()
        self.addCleanup(push_patcher.stop)
        record_narrative_event(
            source_id="quest:test_001",
            event_type="quest_completion",
            content={
                "location": {"id": str(self.player.pk), "label": "frozen tick room"},
                "quest_id": "q1",
                "definition_key": "dk1",
                "completed_objective": "obj",
                "outcome": "completed",
            },
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_reads = 0

        def _read_clock():
            self.clock_reads += 1
            return self.clock

        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock",
            side_effect=_read_clock,
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_admission_and_completion_report_the_frozen_tick(self):
        with patch.object(service, "log_info") as info:
            deferred = self._schedule(_good_client(), trigger="wake")
            self.assertIsNotNone(deferred)
            self.assertTrue(deferred.result)

        self.assertEqual(self.clock_reads, 1)
        events = [call for call in info.call_args_list if call.args]
        names = [call.args[0] for call in events]
        self.assertIn("title_nomination_admitted", names)
        self.assertIn("title_nomination_completed", names)
        admitted = next(
            call.kwargs["context"]
            for call in events
            if call.args[0] == "title_nomination_admitted"
        )
        completed = next(
            call.kwargs["context"]
            for call in events
            if call.args[0] == "title_nomination_completed"
        )
        self.assertEqual(admitted["frozen_tick"], 100)
        self.assertEqual(completed["frozen_tick"], 100)
        self.assertEqual(admitted["source_count"], 1)
        self.assertEqual(completed["source_count"], 1)
        self.assertEqual(completed["candidate_count"], 3)
        self.assertTrue(completed["persisted"])
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_explicit_tick_reads_no_clock(self):
        deferred = self._schedule(_good_client(), frozen_tick=100)
        self.assertIsNotNone(deferred)
        self.assertEqual(self.clock_reads, 0)
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_clock_advancing_during_generation_keeps_the_admitted_window(self):
        clock = self.clock
        day = title_rules._DAY_SECONDS

        class AdvancingClient:
            def get_response(self, descriptor):
                # Gameplay time advances while the model round is pending.
                clock.tick = 40 * day
                return defer.succeed(
                    _reply(
                        [
                            {
                                "display": "火焰之心",
                                "basis": "焚盡匪寨",
                                "source_ids": ["quest:test_001"],
                            }
                        ]
                        * 5
                    )
                )

        with patch.object(service, "log_info") as info:
            deferred = service.schedule_epithet_nomination(
                self.player, client=AdvancingClient(), trigger="wake"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        self.assertEqual(self.clock_reads, 1)
        completed = next(
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "title_nomination_completed"
        )
        self.assertEqual(completed["frozen_tick"], 100)
        # The citation resolves only inside the admitted two-day window; a
        # recalculated window would have eliminated every candidate.
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_generation_failure_reports_the_frozen_tick(self):
        with (
            patch(
                "world.ai.title_nomination.generate_epithet_candidates",
                side_effect=RuntimeError("model transport failed"),
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(
                self.player, client=_good_client(), trigger="wake"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        failures = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_generation_failed"
        ]
        self.assertEqual(len(failures), 1)
        context = failures[0].kwargs["context"]
        self.assertEqual(context["frozen_tick"], 100)
        self.assertEqual(context["trigger"], "wake")
        self.assertEqual(context["player"], str(self.player.pk))
        self.assertEqual(context["source_count"], 1)
        self.assertFalse(title_rules.safe_pending_ballot(self.player))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_persistence_failure_reports_the_frozen_tick(self):
        with (
            patch(
                "world.rules.titles.persist_nomination_ballot",
                side_effect=RuntimeError("ballot write failed"),
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(
                self.player, client=_good_client(), trigger="logout"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        failures = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_generation_failed"
        ]
        self.assertEqual(len(failures), 1)
        context = failures[0].kwargs["context"]
        self.assertEqual(context["frozen_tick"], 100)
        self.assertEqual(context["trigger"], "logout")
        self.assertEqual(context["source_count"], 1)
        self.assertFalse(title_rules.safe_pending_ballot(self.player))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_unavailable_clock_ends_the_workflow_without_side_effects(self):
        client = _good_client()
        title_state_before = title_rules.read_title_state(self.player)
        with (
            patch(
                "server.title_nomination_service.read_world_clock",
                return_value=None,
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(self.player, client=client)

        self.assertIsNone(deferred)
        self.assertEqual(client.calls, [])
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)
        self.assertEqual(title_rules.read_title_state(self.player), title_state_before)
        unavailable = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_clock_unavailable"
        ]
        self.assertEqual(len(unavailable), 1)

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_client_build_failure_reports_the_admitted_workflow(self):
        with (
            patch.object(
                service,
                "_build_nomination_client",
                side_effect=RuntimeError("client construction failed"),
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(
                self.player, trigger="logout"
            )

        self.assertIsNone(deferred)
        failures = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_scheduling_failed"
        ]
        self.assertEqual(len(failures), 1)
        context = failures[0].kwargs["context"]
        self.assertEqual(context["player"], str(self.player.pk))
        self.assertEqual(context["trigger"], "logout")
        self.assertEqual(context["frozen_tick"], 100)
        self.assertEqual(context["source_count"], 1)
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_late_generation_errback_reports_the_admitted_workflow(self):
        from twisted.python.failure import Failure

        with patch.object(service, "log_warn") as warn:
            service._log_generation_error(
                Failure(RuntimeError("late failure")),
                player_id=str(self.player.pk),
                trigger="wake",
                frozen_tick=4321,
                source_count=3,
            )

        context = warn.call_args.kwargs["context"]
        self.assertEqual(context["player"], str(self.player.pk))
        self.assertEqual(context["trigger"], "wake")
        self.assertEqual(context["frozen_tick"], 4321)
        self.assertEqual(context["source_count"], 3)
