"""Tests for the composition root that schedules scene-flavor generations.

Covers ``schedule_scene_flavor`` bridging the guarded flavor layer to the
deterministic ``apply_scene_flavor`` write: an enabled profile applies + pushes
on success through a FakeLLMClient; a disabled profile resolves to no flavor
with zero client calls (and no live client ever constructed); synchronous
failures (unregistered layer, malformed context, client-construction failure)
log and return normally without raising to the caller; a Deferred failure path
logs and resolves to nothing; and the module defers every ``world.ai`` import
so a cold import binds no guardrail logger.
"""

from unittest.mock import patch
import unittest

from django.db import transaction
from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom, InstanceRoom
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.maps.bootstrap import sync_grid
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.runtime import accept_quest
from world.quests.scene_builder import apply_scene_flavor
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY

from commands.scene import CmdEnterScene
from tools.spec_traceability import covers_requirement

from server.scene_flavor_service import SceneFlavorContextError, schedule_scene_flavor

_VALID_FLAVOR = (
    "祭壇的苔石在幽暗中泛著微光，潮濕的泥土氣味與燃過的薰香交織，"
    "耳邊只有風穿過石縫的低鳴，靜得彷彿整座森林都在屏息凝視。"
)


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _context(**overrides):
    context = {
        "scene_sentence": "古老森林深處的祭壇，石面上刻滿符文。",
        "quest_context": "採集任務：深入遺忘森林採集靈藥草",
        "room_name": "林間祭壇",
        "region": "遺忘森林",
    }
    context.update(overrides)
    return context


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _install_scene_flavor():
    """Install the scene-flavor layer idempotently after any module reload.

    Mirrors ``_install_scenario_director``: clearing the guardrail entries and
    re-registering through the live module keeps every later consumer
    deterministic regardless of test order.
    """
    from world.ai import guardrail, scene_flavor

    guardrail._semantic_validators.pop("scene_builder", None)
    guardrail._degrade_fallbacks.pop("scene_builder", None)
    scene_flavor.register_scene_flavor()


class SceneFlavorServiceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        _install_scene_flavor()
        self.room = create_object(InstanceRoom, key="flavor-room", location=None)
        self.player = create_object(PlayerCharacter, key="flavor-player")
        self.player.location = self.room

    def tearDown(self):
        from world.ai import guardrail

        guardrail._semantic_validators.pop("scene_builder", None)
        guardrail._degrade_fallbacks.pop("scene_builder", None)
        super().tearDown()

    @covers_requirement("scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_enabled_profile_applies_and_pushes_on_success(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw()):
            with patch.object(self.player, "msg") as player_msg:
                d = schedule_scene_flavor(self.room, _context(), client=client)
                await_result(d)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self.room.db.scene_flavor, _VALID_FLAVOR)
        sent = [str(call.args[0]) for call in player_msg.call_args_list if call.args]
        self.assertIn(_VALID_FLAVOR, sent)

    @covers_requirement("scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_apply_happens_once_and_only_present_players_receive_the_push(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        second = create_object(PlayerCharacter, key="second-player")
        second.location = self.room
        seen = []

        def record_msg(text=None, **kwargs):
            seen.append(text)

        self.player.msg = lambda *args, **kwargs: None
        second.msg = record_msg
        with override_settings(LLM_PROFILES=_raw()):
            d = schedule_scene_flavor(self.room, _context(), client=client)
            await_result(d)
        self.assertEqual(self.room.db.scene_flavor, _VALID_FLAVOR)
        self.assertEqual(seen, [_VALID_FLAVOR])
        self.assertFalse(
            apply_scene_flavor(self.room, "第二次生成的氛圍。"),
            "the write is idempotent even through the deterministic helper",
        )
        self.assertEqual(self.room.db.scene_flavor, _VALID_FLAVOR)

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_disabled_profile_resolves_to_no_flavor_with_zero_client_calls(self):
        disabled = _raw(scene_builder={"enabled": False})
        client = FakeLLMClient()
        with (
            override_settings(LLM_PROFILES=disabled),
            patch(
                "world.ai.client.OpenAICompatClient",
                side_effect=AssertionError(
                    "must not construct the live client when the profile is disabled"
                ),
            ),
        ):
            d = schedule_scene_flavor(self.room, _context(), client=client)
            await_result(d)
        self.assertIsNone(self.room.db.scene_flavor)
        self.assertEqual(len(client.calls), 0)

    def test_offline_stub_is_used_when_no_client_is_injected_and_profile_disabled(self):
        disabled = _raw(scene_builder={"enabled": False})
        with (
            override_settings(LLM_PROFILES=disabled),
            patch(
                "world.ai.client.OpenAICompatClient",
                side_effect=AssertionError(
                    "must not construct the live client when the profile is disabled"
                ),
            ),
        ):
            d = schedule_scene_flavor(self.room, _context())
            await_result(d)
        self.assertIsNone(self.room.db.scene_flavor)

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_malformed_context_logs_and_returns_normally(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            for bad in (
                None,
                "not a dict",
                {},
                {"scene_sentence": "只有一句"},
                {**_context(), "extra": "x"},
                {**_context(), "region": 42},
            ):
                with self.subTest(bad=bad):
                    self.assertIsNone(
                        schedule_scene_flavor(self.room, bad, client=client)
                    )
            self.assertEqual(len(client.calls), 0)
            self.assertIsNone(self.room.db.scene_flavor)

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_unregistered_layer_logs_and_returns_normally(self):
        from world.ai import guardrail

        guardrail._semantic_validators.pop("scene_builder", None)
        guardrail._degrade_fallbacks.pop("scene_builder", None)
        client = FakeLLMClient()
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch("evennia.logger.log_warn") as log_warn,
        ):
            d = schedule_scene_flavor(self.room, _context(), client=client)
            await_result(d)
        self.assertIsNone(self.room.db.scene_flavor)
        self.assertEqual(len(client.calls), 0)
        logged = " ".join(str(call.args[0]) for call in log_warn.call_args_list)
        self.assertIn("scene flavor generation failed", logged)

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_client_construction_failure_logs_and_returns_normally(self):
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch(
                "world.ai.client.OpenAICompatClient",
                side_effect=RuntimeError("injected client construction failure"),
            ),
        ):
            self.assertIsNone(schedule_scene_flavor(self.room, _context()))
        self.assertIsNone(self.room.db.scene_flavor)

    def test_transport_failure_resolves_to_no_flavor_without_raising(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = schedule_scene_flavor(self.room, _context(), client=client)
            await_result(d)
        self.assertIsNone(self.room.db.scene_flavor)
        self.assertEqual(len(client.calls), 1)

    def test_module_imports_before_server_initialization_without_binding_a_logger(self):
        import ast
        from pathlib import Path

        module_path = Path(__file__).resolve().parents[2] / "scene_flavor_service.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.ImportFrom):
                names = [node.module]
            else:
                names = [alias.name for alias in node.names]
            for name in names:
                if name and (name == "world.ai" or name.startswith("world.ai.")):
                    self.fail(
                        f"module-level import {name} would bind a logger; "
                        "world.ai imports must be deferred to the call path"
                    )

    def test_service_and_scene_builder_tests_never_construct_the_live_client(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        for relative in (
            "server/conf/tests/test_scene_flavor_service.py",
            "world/quests/tests/test_scene_builder.py",
        ):
            source = (repo / relative).read_text(encoding="utf-8")
            client_constructor = "OpenAICompatClient" + "("
            socket_import = "import so" + "cket"
            socket_from = "from so" + "cket"
            self.assertNotIn(client_constructor, source, relative)
            self.assertNotIn(socket_import, source, relative)
            self.assertNotIn(socket_from, source, relative)

    def test_context_error_is_a_named_value_error(self):
        from server.scene_flavor_service import _validate_flavor_context

        self.assertTrue(issubclass(SceneFlavorContextError, ValueError))
        with self.assertRaises(SceneFlavorContextError):
            _validate_flavor_context({"scene_sentence": "only-one-key"})


def _instance_bound_payload(**overrides):
    payload = {
        "name": "討伐林間盜匪",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": None},
                "location_req": {
                    "layer": "instance",
                    "archetype": "forest_path",
                    "anchor_key": None,
                    "anchor_near": "capital_altoria",
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [{"role": "bandit", "tier": "bandit", "disposition": None}],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


class SceneFlavorCommandCompositionTests(QuestRegistryIsolation, EvenniaTest):
    """CmdEnterScene schedules exactly one generation on commit (design D2)."""

    def setUp(self):
        super().setUp()
        _install_scene_flavor()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        create_object("typeclasses.rooms.Room", key="虛境", location=None)
        sync_grid()
        self.anchor = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.assertIsNotNone(self.anchor)
        self.player = create_object(PlayerCharacter, key="flavor-enter-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.anchor
        compiled = compile_quest_blueprint(_instance_bound_payload())
        register_generated_quest(compiled)
        accept_quest(self.player, compiled.definition.key)

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        from world.ai import guardrail

        guardrail._semantic_validators.pop("scene_builder", None)
        guardrail._degrade_fallbacks.pop("scene_builder", None)
        super().tearDown()

    def _enter(self):
        enter = CmdEnterScene()
        enter.caller = self.player
        enter.cmdstring = "進入"
        enter.args = ""
        with patch.object(self.player, "msg"):
            enter.parse()
            enter.func()
        return enter

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_enter_schedules_exactly_one_generation_on_commit(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch(
                "server.scene_flavor_service._build_scene_flavor_client",
                return_value=client,
            ),
        ):
            with patch.object(self.player, "msg") as player_msg:
                with self.captureOnCommitCallbacks(execute=True) as callbacks:
                    self._enter()
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(client.calls), 1)
        self.assertIsInstance(self.player.location, InstanceRoom)
        self.assertEqual(self.player.location.db.scene_flavor, _VALID_FLAVOR)
        sent = [str(call.args[0]) for call in player_msg.call_args_list if call.args]
        self.assertIn(
            _VALID_FLAVOR,
            sent,
            "the entering player must receive the push after the traversal",
        )

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation", "scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_enter_registers_after_traversal_so_the_push_reaches_the_player(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch(
                "server.scene_flavor_service._build_scene_flavor_client",
                return_value=client,
            ),
        ):
            with patch.object(self.player, "msg") as player_msg:
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    self._enter()
                self.assertEqual(len(callbacks), 1)
                self.assertIsInstance(
                    self.player.location,
                    InstanceRoom,
                    "registration happens only after a successful traversal",
                )
                for callback in callbacks:
                    callback()
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self.player.location.db.scene_flavor, _VALID_FLAVOR)
        sent = [str(call.args[0]) for call in player_msg.call_args_list if call.args]
        self.assertIn(
            _VALID_FLAVOR,
            sent,
            "the push must reach the player who has already traversed into the room",
        )

    @covers_requirement("scene-flavor::instance-quest-scenes-schedule-one-post-commit-flavor-generation")
    def test_nested_outer_rollback_never_fires_a_generation(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch(
                "server.scene_flavor_service._build_scene_flavor_client",
                return_value=client,
            ),
        ):
            with transaction.atomic():
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    self._enter()
                transaction.set_rollback(True)
            self.assertNotEqual(
                callbacks, [], "the command must register the scheduling"
            )
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(
            InstanceRoom.objects.count(),
            0,
            "the rollback must also undo the materialized scene in the database",
        )


if __name__ == "__main__":
    unittest.main()
