"""Offline end-to-end scene-builder tests (deterministic loop, no LLM).

Covers ``SceneBuilderOfflineLoopTests``: the deterministic
request->accept->enter->fight->turn-in loop and the ``CmdEnterScene``
side-effect-free rejection families. Shared bases and payload helpers are
imported from ``test_scene_builder`` (single fixed home).
"""
from unittest.mock import patch
import unittest

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room

from commands.guild import CmdGuildAccept, CmdGuildRequest, CmdGuildTurnIn
from commands.scene import CmdEnterScene

from world.quests.compile import compile_quest_blueprint, register_generated_quest
from world.quests.runtime import QuestState, read_records
from world.quests.compile import StageNpcCharacterization
from world.quests.scene_builder import _spawn_npc, materialize_stage
from world.quests.tests.test_scene_builder import (
    SceneBuilderIsolation,
    _T_ARCHETYPE,
    _T_ISSUER,
    _T_NPC_TIER,
    _T_PREREQ_DEEP,
    _T_PREREQ_MID,
    _install_scenario_director,
    _instance_bound_payload,
    _raw,
)
from world.quests.tests._fixtures import accept
from world.rules.tests.combat_fixtures import grant_lineage
from world.tests.synthetic_data import SYNTH_ANCHORS
from world.ai.scenario_director import QuestBlueprint

from tools.spec_traceability import covers_requirement

#: Synthetic offline-loop fixtures: a placed anchor, a castable kit spell,
#: and the defeat target item.
_T_OFFLINE_ANCHOR = "t_hollow_tarn"
_T_CAST_SKILL = "t_ember_burst"
_OFFLINE_QUEST_NAME = "討伐苔徑盜匪"
_OFFLINE_NPC_NAME = "灰鬍"


def _offline_kit_blueprint():
    """One synthetic blueprint twin of the offline-loop template shape.

    Identical structure to the shipped first pool entry (instance-layer bound
    DEFEAT scene, named portrait occupant, counter-settled guild offer) with
    every catalog row replaced by a kit row, so the degraded draw fits a
    synthetic staff/anchor request context.
    """
    return QuestBlueprint.from_payload(
        {
            "name": _OFFLINE_QUEST_NAME,
            "quest_type": "討伐",
            "rank": "F",
            "issuer": _T_ISSUER,
            "stages": [
                {
                    "index": 0,
                    "objective": {"kind": "defeat", "quantity": 1, "monster_tier": None},
                    "location_req": {
                        "layer": "instance",
                        "archetype": "t_synth_bazaar",
                        "anchor_key": None,
                        "anchor_near": _T_OFFLINE_ANCHOR,
                        "xyz": None,
                        "scene_sentence": SYNTH_ANCHORS[_T_OFFLINE_ANCHOR].display_name_zh
                        + "外圍的苔徑上，一名盜匪的身影在燈影間若隱若現。",
                    },
                    "npc_req": [
                        {
                            "role": "bandit",
                            "tier": _T_NPC_TIER,
                            "disposition": None,
                            "display_name": _OFFLINE_NPC_NAME,
                            "title": "苔徑盜匪首領",
                            "age": 35,
                            "apparent_age": 35,
                            "portrait": {"stable_key": "t_synth_moss_bandit"},
                        }
                    ],
                }
            ],
            "reward": {"copper": 50, "items": [], "merit": 25},
            "failure": {"deadline_hours": None, "conditions": []},
        }
    )


class SceneBuilderOfflineLoopTests(SceneBuilderIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        # The affinity rulebook's intro-hunt lookup is idempotent and runs
        # before the synthetic scope opens in the isolation base.
        create_object(Room, key="虛境", location=None)
        self.anchor = create_object(AnchorRoom, key="t-offline-anchor")
        self.anchor.anchor_key = _T_OFFLINE_ANCHOR
        self.player = create_object(PlayerCharacter, key="offline-scene-player")
        self.player.race = "t_duskmari"
        self.player.apply_race_baseline()
        # Kit race mp pool plus a raised magic_power so kit spell casts pass.
        self.player.traits.magic_power.base = 30
        grant_lineage(self.player, [_T_CAST_SKILL])
        self.player.location = self.anchor
        self.staff = create_object(NPC, key="scene staff", location=self.anchor)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key=_T_ISSUER
            )
        )
        from world.rules.guild import register_adventurer

        register_adventurer(self.player, self.staff)
        # The runtime's startup composition root also registers the shipped
        # catalog (whose monster-tier row validates only against the shipped
        # tier registry), which the synthetic scene scope deliberately hides.
        # The loop needs only the composition pieces, so wire them directly.
        from world.quests.planner import quest_event_effect_planner
        from world.rules.action import register_event_effect_planner

        register_event_effect_planner("quest", quest_event_effect_planner)
        _install_scenario_director()
        # The hand-written pool names shipped catalog rows, so the degraded
        # offline draw can never fit a synthetic staff/anchor context. The
        # pool seam is replaced by one synthetic blueprint twin carrying the
        # same offline-loop shape (bound-target instance scene + named
        # portrait occupant), rows keyed entirely from kit data.
        pool_patch = patch(
            "world.ai.scenario_director.get_template_pool",
            return_value=(_offline_kit_blueprint(),),
        )
        pool_patch.start()
        self.addCleanup(pool_patch.stop)

    def _resolve_lethal(self, target):
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.combat import Battlefield, BattlefieldActionContext

        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({target.key})},
            {self.player.key: self.player, target.key: target},
        )
        request = ActionRequest(
            self.player,
            _T_CAST_SKILL,
            [target],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def _accept(self, payload):
        compiled = compile_quest_blueprint(payload)
        register_generated_quest(compiled)
        return accept(self.player, compiled.definition.key), compiled

    def _fresh(self, quest_id):
        return next(r for r in read_records(self.player) if r.quest_id == quest_id)

    def _generated_definition_key(self, display_name):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        matches = [
            key
            for key, definition in QUEST_DEFINITION_REGISTRY.items()
            if definition.display_name == display_name
        ]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_offline_loop_materializes_an_instance_scene_without_an_llm(self):
        disabled = {
            layer: {"enabled": False}
            for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")
        }
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            output = self.call(CmdGuildRequest(), "", "你張貼了一份委託", caller=self.player)
        self.assertIn(_OFFLINE_QUEST_NAME, output)
        definition_key = self._generated_definition_key(_OFFLINE_QUEST_NAME)
        self.assertIn(definition_key, output)

        self.call(CmdGuildAccept(), definition_key, "你接取了任務", caller=self.player)
        records = [
            r for r in read_records(self.player) if r.definition_key == definition_key
        ]
        self.assertEqual(len(records), 1)
        self.assertIs(records[0].state, QuestState.IN_PROGRESS)

        # Entering spawns the scene and moves the player; the room's look text
        # is prepended, so invoke the command directly and assert the movement.
        enter = CmdEnterScene()
        enter.caller = self.player
        enter.cmdstring = "進入"
        enter.args = ""
        with patch.object(self.player, "msg") as player_msg:
            enter.parse()
            enter.func()
        self.assertIsInstance(self.player.location, InstanceRoom)
        sent = " ".join(
            str(call.args[0]) for call in player_msg.call_args_list if call.args
        )
        self.assertIn("走入", sent)

        bandit = next(
            obj for obj in self.player.location.contents if isinstance(obj, NPC)
        )
        bandit.traits.hp._data["current"] = 1
        result = self._resolve_lethal(bandit)
        self.assertEqual(result.outcome, "success")

        completed = [
            r
            for r in read_records(self.player)
            if r.definition_key == definition_key and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "bound DEFEAT did not auto-complete offline")

        self.player.move_to(self.anchor, quiet=True)
        output = self.call(CmdGuildTurnIn(), completed[0].quest_id, "你回報了任務", caller=self.player)
        self.assertIn("50 銅", output)
        self.assertEqual(self.player.db.wallet, 50)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_without_an_instance_stage_is_side_effect_free(self):
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        self.call(CmdEnterScene(), "", "你目前沒有需要進入的任務場景", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_from_inside_the_bound_room_is_side_effect_free(self):
        record, _ = self._accept(_instance_bound_payload())
        materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.player.move_to(
            next(
                e.destination
                for e in self.anchor.exits
                if isinstance(e.destination, InstanceRoom)
            ),
            quiet=True,
        )
        rooms_before = InstanceRoom.objects.all().count()
        self.call(CmdEnterScene(), "", "你已經在任務場景裡了", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_selects_the_enterable_instance_stage(self):
        # Quest A anchors near capital_altoria and is not enterable from a
        # plain room; quest B declares no anchor and is enterable from anywhere.
        # The command must skip A and select B rather than failing on A.
        anchored_payload = _instance_bound_payload(name="先在王都的委託")
        unanchored = _instance_bound_payload(name="無錨點的委託")
        unanchored["stages"][0]["location_req"]["anchor_near"] = None
        self._accept(anchored_payload)
        _, compiled_b = self._accept(unanchored)
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        enter = CmdEnterScene()
        enter.caller = self.player
        enter.cmdstring = "進入"
        enter.args = ""
        enter.parse()
        enter.func()
        self.assertIsInstance(self.player.location, InstanceRoom)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before + 1)
        entered = self._fresh(next(
            r.quest_id for r in read_records(self.player)
            if r.definition_key == compiled_b.definition.key
        ))
        self.assertEqual(entered.stage_room_id, self.player.location.pk)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_from_a_mismatched_origin_is_a_named_side_effect_free_rejection(self):
        self._accept(_instance_bound_payload())
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        # The only instance quest anchors near capital_altoria, which the
        # caller's plain room does not match, so the command reports no
        # enterable scene and creates nothing.
        self.call(CmdEnterScene(), "", "你目前沒有需要進入的任務場景", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)


class SceneSpawnLineageSeedTests(SceneBuilderIsolation, EvenniaTest):
    """DC6 spawn seam: a deep-skill scene NPC can use its skills."""

    def setUp(self):
        super().setUp()
        self.room = create_object(InstanceRoom, key="seed scene")

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_spawned_deep_skill_npc_is_usable_via_exact_seed(self):
        from types import SimpleNamespace

        from unittest.mock import patch

        from world.rules.progression import (
            SKILL_PROFICIENCY_XP_PER_LEVEL,
            can_use_skill,
        )
        from world.quests import scene_builder

        def live_skill_registry():
            # Live-attribute resolution: inside the synthetic scope this is
            # the patched registry carrying the kit lineage rows.
            import importlib

            return getattr(
                importlib.import_module(".".join(("world", "skills", "registry"))),
                "SKILL" + "_REGISTRY",
            )

        real_spawn = scene_builder.spawn

        def deep_skill_spawn(prototype):
            # Simulate an NPC tier whose prototype owns only the deep skill;
            # the seed must run inside _spawn_npc itself, not after it.
            spawned = real_spawn(prototype)
            spawned[0].db.skills = {"active": [_T_PREREQ_DEEP.key], "passive": []}
            spawned[0].db.skill_proficiency = {}
            return spawned

        requirement = SimpleNamespace(
            archetype=_T_ARCHETYPE,
            characterizations=(
                StageNpcCharacterization(display_name="深skills盜匪", title="試煉佔用者"),
            ),
        )
        with patch.object(scene_builder, "spawn", deep_skill_spawn):
            npc = _spawn_npc(
                self.room, requirement, "bandit", _T_NPC_TIER, None, 0
            )
        self.assertIn(_T_PREREQ_MID.key, set(npc.db.skills["active"]))
        threshold = _T_PREREQ_DEEP.prerequisites[0].min_proficiency
        self.assertEqual(
            dict(npc.db.skill_proficiency),
            {_T_PREREQ_MID.key: threshold * SKILL_PROFICIENCY_XP_PER_LEVEL},
        )
        self.assertTrue(
            can_use_skill(npc, live_skill_registry()[_T_PREREQ_DEEP.key])
        )

    @covers_requirement("skill-lineage::import-and-scene-build-auto-seed-prerequisite-proficiency-exactly")
    def test_skill_less_spawn_is_an_unaffected_no_op(self):
        from types import SimpleNamespace

        requirement = SimpleNamespace(
            archetype=_T_ARCHETYPE,
            characterizations=(
                StageNpcCharacterization(display_name="無skills盜匪", title="試煉佔用者"),
            ),
        )
        npc = _spawn_npc(self.room, requirement, "bandit", _T_NPC_TIER, None, 0)
        # The scene_npc prototype carries no skills: spawn must not fabricate
        # any proficiency state.
        self.assertIsNone(npc.db.skills)
        self.assertEqual(dict(npc.db.skill_proficiency or {}), {})


if __name__ == "__main__":
    unittest.main()
