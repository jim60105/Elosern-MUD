"""Offline runtime path, cross-change contract, and source-guard tests (9.1-9.6)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from commands.action import CmdCast
from world.quests.binding import bind_stage_runtime
from world.quests.bootstrap import sync_quest_runtime
from world.quests.catalog import register_catalog
from world.quests.runtime import (
    QuestState,
    accept_quest,
    read_records,
    to_storage,
)
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    _EVENT_EFFECT_PLANNERS,
    register_event_effect_planner,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    default_attack_policy,
    run_round,
)
from world.rules.overwhelm import resolve_overwhelm
from world.rules.tests.combat_fixtures import grant_lineage

from ._fixtures import QuestRegistryIsolation, defeat, quest, register

QUESTS_ROOT = Path(__file__).resolve().parents[2]


class OfflineRuntimePathTests(QuestRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        sync_quest_runtime()
        self.player = create_object(PlayerCharacter, key="offline-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human static magic_power at 術師 tier so fire_ball casts pass.
        self.player.traits.magic_power.base = 30
        grant_lineage(self.player, ["fire_ball"])

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve_lethal(self, monster: Monster):
        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({monster.key})},
            {self.player.key: self.player, monster.key: monster},
        )
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    # NOTE: this API-level seam is NOT a player-command acceptance test. Change
    # 16 must supply player-facing accept, combat entry, and turn-in before the
    # player-playable Phase-4 milestone can be claimed (design.md Open Questions).
    @covers_requirement("quest-progress-tracking::change-15-exposes-a-deterministic-no-ai-completion-seam-for-phase-4")
    def test_hand_written_hunt_completes_without_ai_or_manual_progress(self):
        record = accept_quest(self.player, "introductory_hunt")
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        monster = self._monster("offline-goblin")
        result = self._resolve_lethal(monster)
        self.assertEqual(result.outcome, "success")
        completed = [to_storage(r) for r in read_records(self.player)][0]
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(completed["quest_id"], record.quest_id)
        quest_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in QUESTS_ROOT.glob("world/quests/*.py")
        )
        self.assertNotIn("world.ai", quest_source)


class PlannerExecutionPathsTests(QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.calls: list[str] = []
        sync_quest_runtime()
        original = _EVENT_EFFECT_PLANNERS["quest"]

        def spy(request, event_log):
            self.calls.append("quest")
            return original(request, event_log)

        register_event_effect_planner("quest", spy)
        self.player = create_object(PlayerCharacter, key="path-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human static magic_power at 術師 tier so fire_ball casts pass.
        self.player.traits.magic_power.base = 30
        grant_lineage(self.player, ["fire_ball"])

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _field(self, actor, targets):
        return Battlefield(
            {"party": frozenset({actor.key}), "foes": frozenset(t.key for t in targets)},
            {actor.key: actor, **{t.key: t for t in targets}},
        )

    def test_direct_resolver_use_executes_the_planner_exactly_once(self):
        monster = self._monster("direct")
        field = self._field(self.player, [monster])
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.calls.count("quest"), 1)

    def test_out_of_combat_cast_executes_the_planner(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {"active": ["status_disguise"], "passive": []}
        from world.rules.clock import WorldClock

        clock = WorldClock()
        with patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), "status_disguise", f"{self.char1.key} 改變了")
        self.assertEqual(self.calls.count("quest"), 1)

    def test_combat_round_executes_the_planner(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # Human static magic_power at 術師 tier so fire_ball casts pass.
        self.char1.traits.magic_power.base = 30
        grant_lineage(self.char1, ["fire_ball"])
        monster = self._monster("round")
        field = self._field(self.char1, [monster])
        with patch("world.rules.combat.roll_d100", return_value=100):
            run_round(
                field,
                lambda entity, field: (
                    default_attack_policy(entity, field)
                    if isinstance(entity, PlayerCharacter)
                    else None
                ),
            )
        self.assertFalse(monster.traits.hp.current > 0)
        self.assertEqual(self.calls.count("quest"), 1)

    def test_overwhelm_path_executes_the_planner(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            trait = getattr(self.player.traits, key)
            trait.base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        monster = self._monster("overwhelmed", hp=1)
        field = self._field(self.player, [monster])
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = resolve_overwhelm(field, default_attack_policy)
        self.assertTrue(result.battle_over)
        self.assertGreaterEqual(self.calls.count("quest"), 1)


class Change16ReadContractTests(QuestRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.player = create_object(PlayerCharacter, key="contract16")
        self.player.race = "human"
        self.player.apply_race_baseline()

    def test_completed_record_is_readable_without_paying_a_reward(self):
        definition = register(quest("contract16_simple"))
        with patch("world.quests.runtime._current_tick", return_value=10):
            record = accept_quest(self.player, definition.key)
        self.assertIsNotNone(record)
        # Change 16 obligation: guild accept/turn-in, combat entry, and reward
        # settlement live outside this change; reading a COMPLETED record must
        # be sufficient for that work. No wallet or turn-in exists here.
        from world.quests import runtime as quest_runtime

        exported = {
            name
            for name, _ in inspect.getmembers(quest_runtime, inspect.isfunction)
        }
        self.assertNotIn("settle_reward", exported)
        self.assertNotIn("grant_guild_merit", exported)


class Change21BindContractTests(QuestRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="contract21")
        self.player.race = "human"
        self.player.apply_race_baseline()
        from world.quests.definitions import QuestStage

        from ._fixtures import defeat as _defeat

        self.bound_def = register(
            quest(
                "contract21_bound_defeat",
                stages=(QuestStage(0, _defeat(bound=True)),),
            )
        )

    def test_already_created_instance_and_entities_can_be_bound(self):
        from typeclasses.npcs import NPC
        from typeclasses.rooms import InstanceRoom

        room = create_object(InstanceRoom, key="contract21-room")
        target = create_object(NPC, key="contract21-target")
        target.race = "human"
        target.apply_race_baseline()
        record = accept_quest(self.player, self.bound_def.key)
        bound = bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(target,),
        )
        self.assertEqual(bound.stage_room_id, room.pk)
        self.assertEqual(bound.objective_target_ids, (target.pk,))
        self.assertTrue(room.db.pin_reasons)


class QuestSourceGuardTests(unittest.TestCase):
    def test_world_quests_has_no_ai_llm_or_spawn_usage(self):
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in QUESTS_ROOT.glob("world/quests/*.py")
        )
        self.assertNotIn("world.ai", source)
        self.assertNotIn("llm", source.lower())
        self.assertNotIn("prototype", source.lower())
        self.assertNotIn("spawn(", source)

    def test_no_public_acquire_progress_forge_entry_point(self):
        import world.quests as quests_package
        import pkgutil

        # Change 16 adds the internal `acquire` module that computes progress
        # from committed inventory plans (guild-economy D-5). There must be no
        # PUBLIC caller-facing "acquire something" assertion API: the only
        # accepted entry point is `compute_acquire_replacement(entity,
        # additions)`, which requires a positive committed plan additions
        # argument and is consumed by the equipment planner.
        for module_info in pkgutil.walk_packages(
            quests_package.__path__,
            prefix="world.quests.",
        ):
            if not module_info.name.startswith("world.quests.tests"):
                module = __import__(module_info.name, fromlist=["*"])
                for name in dir(module):
                    if name.startswith("_") or name == "compute_acquire_replacement":
                        continue
                    if "acquire" in name.lower():
                        self.fail(
                            f"{module_info.name} exposes a caller-facing "
                            f"acquire entry point {name!r}"
                        )


if __name__ == "__main__":
    unittest.main()
