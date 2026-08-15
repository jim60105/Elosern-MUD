"""Tests for action-driven quest progress and protected-entity failure (6.1-6.4)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, Room
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage, QuestType
from world.quests.planner import quest_event_effect_planner
from world.quests.runtime import (
    QuestState,
    accept_quest,
    read_records,
    to_storage,
)
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    register_event_effect_planner,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.party import join_party
from world.rules.targeting import RoomActionContext
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

from ._fixtures import (
    QuestRegistryIsolation,
    anchor_locator,
    defeat,
    escort,
    quest,
    register,
)


CLAW_SKILL = SkillDef(
    key="claw",
    label="利爪",
    description="以利爪撕扯單一敵人。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=False,
    element=None,
    effects=["damage:dark:physical"],
    category=SkillCategory.UTILITY,
)

STRIKE_SKILL = SkillDef(
    key="strike",
    label="突襲",
    description="測試用：對單一敵人造成物理傷害，且可在非戰鬥場合使用。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["damage:dark:physical"],
    category=SkillCategory.UTILITY,
)


class QuestPlannerTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        SKILL_REGISTRY["claw"] = CLAW_SKILL
        self.player = create_object(PlayerCharacter, key="quest-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human starting magic level (術師 tier) so fire_ball casts pass.
        self.player.traits.magic_level.base = 30
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.tier_hunt = register(quest("tier_hunt_three", stages=(QuestStage(0, defeat(quantity=3)),)))
        self.bound_hunt = register(
            quest("bound_hunt", stages=(QuestStage(0, defeat(bound=True)),))
        )
        self.two_stage = register(
            quest(
                "two_stage",
                stages=(
                    QuestStage(0, defeat(quantity=1)),
                    QuestStage(1, defeat(quantity=1)),
                ),
            )
        )
        self.escort_quest = register(
            quest(
                "escort_anchor",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(anchor_locator())),),
            )
        )

    def tearDown(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        SKILL_REGISTRY.pop("claw", None)
        super().tearDown()

    def _monster(self, key: str, hp: int = 1, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _npc(self, key: str, hp: int = 1) -> NPC:
        npc = create_object(NPC, key=key)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp._data["current"] = hp
        return npc

    def _field(self, actor, targets, key_override: str | None = None):
        actor_key = key_override or actor.key
        return Battlefield(
            {"party": frozenset({actor_key}), "foes": frozenset(t.key for t in targets)},
            {actor_key: actor, **{t.key: t for t in targets}},
        )

    def _resolve(self, actor, skill_key, targets):
        field = self._field(actor, targets)
        request = ActionRequest(actor, skill_key, targets, BattlefieldActionContext(field))
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_player_defeat_advances_matching_tier_objective(self):
        accept_quest(self.player, self.tier_hunt.key)
        first = self._monster("a")
        self.assertEqual(self._resolve(self.player, "fire_ball", [first]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 1)
        second = self._monster("b")
        self.assertEqual(self._resolve(self.player, "fire_ball", [second]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 2)
        self.assertEqual(self._records()[0]["state"], "in_progress")

    def test_wrong_tier_kill_grants_no_progress(self):
        accept_quest(self.player, self.tier_hunt.key)
        mid = self._monster("mid", tier="mid")
        self.assertEqual(self._resolve(self.player, "fire_ball", [mid]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    def test_bound_objective_matches_exact_dbref_not_display_key(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        unbound = self._monster("decoy")
        bound = self._monster("real")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(bound,))
        self.assertEqual(self._resolve(self.player, "fire_ball", [unbound]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 0)
        self.assertEqual(self._resolve(self.player, "fire_ball", [bound]).outcome, "success")
        self.assertEqual(self._records()[0]["stage_progress"], 1)

    def test_non_player_actor_grants_no_ordinary_kill_credit(self):
        accept_quest(self.player, self.tier_hunt.key)
        hunter = self._monster("hunter", hp=200, tier="mid")
        hunter.db.skills = {"active": ["claw"], "passive": []}
        prey = self._monster("prey")
        result = self._resolve(hunter, "claw", [prey])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    def test_area_defeat_aggregates_without_skipping_stages(self):
        accept_quest(self.player, self.two_stage.key)
        monsters = [self._monster(f"m{i}") for i in range(3)]
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        result = self._resolve(self.player, "wind_blade", monsters)
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["stage_index"], 1)
        self.assertEqual(stored["stage_progress"], 0)

    def test_final_objective_completes_and_clears_bindings(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        room = create_object(InstanceRoom, key="hunt-room")
        bound = self._monster("final")
        bind_stage_runtime(self.player, record.quest_id, room=room, objective_targets=(bound,))
        result = self._resolve(self.player, "fire_ball", [bound])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["stage_progress"], 1)
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(stored["objective_target_ids"], [])
        self.assertEqual(room.db.pin_reasons, [])

    @covers_requirement("quest-progress-tracking::stage-completion-advances-exactly-once-and-releases-obsolete-runtime-bindings")
    def test_terminal_records_ignore_later_matching_events(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        bound = self._monster("done")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(bound,))
        self._resolve(self.player, "fire_ball", [bound])
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        extra = self._monster("extra")
        self._resolve(self.player, "fire_ball", [extra])
        after = self._records()[0]
        self.assertEqual(after, stored)
        self.assertEqual(after["state"], "completed")

    def test_protected_npc_death_fails_escort_quest(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard")
        room = create_object(InstanceRoom, key="escort-room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        killer = self._monster("killer", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        result = self._resolve(killer, "claw", [guard])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "protected_entity_defeated")
        self.assertEqual(stored["protected_entity_ids"], [])
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(room.db.pin_reasons, [])

    def test_same_display_key_creates_no_false_failure(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard-identical")
        impostor = self._npc("guard-identical")
        guard.db.key = "guard"
        impostor.db.key = "guard"
        bind_stage_runtime(self.player, record.quest_id, protected_entities=(guard,))
        killer = self._monster("killer", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        self._resolve(killer, "claw", [impostor])
        self.assertEqual(self._records()[0]["state"], "in_progress")
        self._resolve(killer, "claw", [guard])
        self.assertEqual(self._records()[0]["state"], "failed")

    def test_objective_target_death_cannot_trigger_protected_failure(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        target = self._monster("objective-target")
        bind_stage_runtime(self.player, record.quest_id, objective_targets=(target,))
        self._resolve(self.player, "fire_ball", [target])
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["failure_reason"], None)

    def test_same_event_protected_failure_wins_over_defeat_progress(self):
        record = accept_quest(self.player, self.bound_hunt.key)
        target = self._monster("dual-target")
        npc_guard = self._npc("dual-guard")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            objective_targets=(target,),
            protected_entities=(npc_guard,),
        )
        self.player.db.skills = {"active": ["wind_blade"], "passive": []}
        result = self._resolve(self.player, "wind_blade", [target, npc_guard])
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "protected_entity_defeated")
        self.assertEqual(stored["objective_target_ids"], [])
        self.assertEqual(stored["protected_entity_ids"], [])

    @covers_requirement("quest-failure-conditions::defeat-of-an-exact-protected-entity-fails-its-active-quests-atomically")
    def test_commit_fault_rolls_back_death_and_quest_failure_together(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("guard-rollback")
        room = create_object(InstanceRoom, key="escort-rollback")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        killer = self._monster("killer-rollback", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        guard_hp_before = guard.traits.hp.current
        room_pins_before = list(room.db.pin_reasons)
        with patch(
            "world.quests.transitions._apply_pin_operations",
            side_effect=RuntimeError("injected pin failure"),
        ):
            result = self._resolve(killer, "claw", [guard])
        from world.rules.action import RejectReason

        self.assertEqual(result.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(guard.traits.hp.current, guard_hp_before)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(room.db.pin_reasons, room_pins_before)


    def test_simulated_defeat_grants_no_defeat_progress(self):
        # A guild examination is a simulated battle: even a tier-matching
        # lethal defeat must not advance a DEFEAT objective.
        accept_quest(self.player, self.tier_hunt.key)
        target = self._monster("simulated-victim")
        field = self._field(self.player, [target])
        request = ActionRequest(
            self.player,
            "fire_ball",
            [target],
            BattlefieldActionContext(
                field,
                event_context={"battlefield": field, "simulated": True},
            ),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(target.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    def test_simulated_defeat_never_fails_protected_entity(self):
        # A simulated lethal crossing on a bound protected entity must not
        # fail its active quest: the battle is a simulation.
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("simulated-guard")
        room = create_object(InstanceRoom, key="simulated-room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        killer = self._monster("simulated-killer", hp=200, tier="mid")
        killer.db.skills = {"active": ["claw"], "passive": []}
        field = self._field(killer, [guard])
        request = ActionRequest(
            killer,
            "claw",
            [guard],
            BattlefieldActionContext(
                field,
                event_context={"battlefield": field, "simulated": True},
            ),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(guard.traits.hp.current, 0)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "in_progress")
        self.assertEqual(stored["protected_entity_ids"], [int(guard.pk)])


class CompanionDefeatCreditTests(QuestRegistryIsolation, EvenniaTest):
    """Companion DEFEAT credit for the quest owner (party-quest task 1.3)."""

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        SKILL_REGISTRY["claw"] = CLAW_SKILL
        SKILL_REGISTRY["strike"] = STRIKE_SKILL
        self.room = create_object(Room, key="companion-room")
        self.player = create_object(PlayerCharacter, key="companion-owner")
        self.player.race = "human"
        self.player.apply_race_baseline()
        # Human starting magic level (術師 tier) so fire_ball casts pass.
        self.player.traits.magic_level.base = 30
        self.player.location = self.room
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.tier_hunt = register(quest("tier_hunt_three", stages=(QuestStage(0, defeat(quantity=3)),)))
        self.two_stage = register(
            quest(
                "two_stage",
                stages=(
                    QuestStage(0, defeat(quantity=1)),
                    QuestStage(1, defeat(quantity=1)),
                ),
            )
        )

    def tearDown(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        SKILL_REGISTRY.pop("claw", None)
        SKILL_REGISTRY.pop("strike", None)
        super().tearDown()

    def _monster(self, key: str, hp: int = 1, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _companion(self, key: str) -> NPC:
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        # Human starting magic level (術師 tier) so elemental companion casts
        # (wind_blade) pass the cast gate.
        npc.traits.magic_level.base = 30
        npc.traits.hp._data["current"] = 1
        npc.db.skills = {"active": ["claw"], "passive": []}
        join_party(npc, self.player)
        return npc

    def _field(self, actor, targets, *, knocked_out: frozenset[str] = frozenset()):
        return Battlefield(
            {"party": frozenset({actor.key}), "foes": frozenset(t.key for t in targets)},
            {actor.key: actor, **{t.key: t for t in targets}},
            knocked_out=set(knocked_out),
        )

    def _resolve(self, actor, skill_key, targets, field):
        request = ActionRequest(
            actor, skill_key, targets, BattlefieldActionContext(field)
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_bound_companion_kill_advances_owner_objective(self):
        accept_quest(self.player, self.tier_hunt.key)
        companion = self._companion("first")
        prey = self._monster("prey")
        field = self._field(companion, [prey])
        result = self._resolve(companion, "claw", [prey], field)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 1)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_knocked_out_companion_kill_grants_no_credit(self):
        accept_quest(self.player, self.tier_hunt.key)
        companion = self._companion("ko")
        prey = self._monster("prey-ko")
        field = self._field(
            companion, [prey], knocked_out=frozenset({companion.key})
        )
        result = self._resolve(companion, "claw", [prey], field)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_unbound_npc_kill_grants_no_credit(self):
        accept_quest(self.player, self.tier_hunt.key)
        outsider = create_object(NPC, key="outsider", location=self.room)
        outsider.race = "human"
        outsider.apply_race_baseline()
        outsider.db.skills = {"active": ["claw"], "passive": []}
        prey = self._monster("prey-unbound")
        field = self._field(outsider, [prey])
        result = self._resolve(outsider, "claw", [prey], field)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    def test_backref_mismatch_kill_grants_no_credit(self):
        accept_quest(self.player, self.tier_hunt.key)
        # The NPC claims the player as its owner but is absent from the
        # player's party list: the one-sided binding must fail closed.
        impostor = create_object(NPC, key="impostor", location=self.room)
        impostor.race = "human"
        impostor.apply_race_baseline()
        impostor.db.skills = {"active": ["claw"], "passive": []}
        impostor.db.party_member = self.player.pk
        prey = self._monster("prey-mismatch")
        field = self._field(impostor, [prey])
        result = self._resolve(impostor, "claw", [prey], field)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    def test_no_battlefield_credit_request_fails_closed(self):
        accept_quest(self.player, self.tier_hunt.key)
        companion = self._companion("striker")
        companion.db.skills = {"active": ["strike"], "passive": []}
        prey = self._monster("prey-ambush")
        prey.location = self.room
        request = ActionRequest(
            companion, "strike", [prey], RoomActionContext(self.room)
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(prey.traits.hp.current, 0)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_companion_area_defeat_aggregates_without_skipping_stages(self):
        accept_quest(self.player, self.two_stage.key)
        companion = self._companion("reaver")
        companion.db.skills = {"active": ["wind_blade"], "passive": []}
        monsters = [self._monster(f"c-m{i}") for i in range(3)]
        field = self._field(companion, monsters)
        result = self._resolve(companion, "wind_blade", monsters, field)
        self.assertEqual(result.outcome, "success")
        stored = self._records()[0]
        self.assertEqual(stored["stage_index"], 1)
        self.assertEqual(stored["stage_progress"], 0)


class UpkeepDefeatPlannerTests(QuestRegistryIsolation, EvenniaTest):
    """fix-dot-kill-credit: the quest planner consumes upkeep-built defeat logs.

    The combat upkeep settlement emits ``EventLog`` values shaped exactly
    like action logs (actor = source key, ``skill_key="combat_upkeep"``,
    ``target_defeated`` entries with ``target_id``/``monster_tier`` data).
    These tests drive the registered quest planner directly with that log
    shape to pin the same aggregation, cap, and one-transition rules the
    action path uses, and the simulated/unattributed skips.
    """

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.player = create_object(PlayerCharacter, key="upkeep-quest-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.tier_hunt = register(
            quest("upkeep_tier_hunt", stages=(QuestStage(0, defeat(quantity=2)),))
        )
        self.two_stage = register(
            quest(
                "upkeep_two_stage",
                stages=(
                    QuestStage(0, defeat(quantity=1)),
                    QuestStage(1, defeat(quantity=1)),
                ),
            )
        )
        self.escort_quest = register(
            quest(
                "upkeep_escort_anchor",
                quest_type=QuestType.ESCORT,
                stages=(QuestStage(0, escort(anchor_locator())),),
            )
        )

    def tearDown(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        super().tearDown()

    def _monster(self, key: str, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = 1
        return monster

    def _npc(self, key: str) -> NPC:
        npc = create_object(NPC, key=key)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp._data["current"] = 1
        return npc

    def _upkeep_log(self, actor, entries):
        from world.rules.event_log import EventLog

        targets = tuple(
            entry.target for entry in entries if entry.target is not None
        )
        return EventLog(
            actor=str(actor.key),
            skill_key="combat_upkeep",
            targets=targets,
            entries=tuple(entries),
            time_cost_seconds=0,
        )

    def _defeat_entry(self, actor, target, *, simulated=False):
        from world.rules.event_log import EventEntry

        data: dict = {
            "target_id": int(target.pk),
            "monster_tier": getattr(target, "threat_tier", None),
        }
        if simulated:
            data["simulated"] = True
        return EventEntry(
            kind="target_defeated",
            actor=str(actor.key),
            target=str(target.key),
            data=data,
            text_template="{actor} 擊敗了 {target}。",
        )

    def _plan(self, actor, entries, battlefield=None):
        from types import SimpleNamespace

        request = SimpleNamespace(
            actor=actor,
            context=SimpleNamespace(battlefield=battlefield),
        )
        return quest_event_effect_planner(request, self._upkeep_log(actor, entries))

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_upkeep_defeat_advances_and_caps_at_the_objective(self):
        accept_quest(self.player, self.tier_hunt.key)
        first = self._monster("u-a")
        second = self._monster("u-b")
        third = self._monster("u-c")
        # The planner is read-only: it returns staged effects and never
        # mutates the record itself (the settlement commits them).
        effects = self._plan(
            self.player,
            [self._defeat_entry(self.player, first)],
        )
        self.assertTrue(effects)
        self.assertEqual(self._records()[0]["stage_progress"], 0)
        effects = self._plan(
            self.player,
            [
                self._defeat_entry(self.player, first),
                self._defeat_entry(self.player, second),
                self._defeat_entry(self.player, third),
            ],
        )
        # Three kills against a quantity-2 objective stage a fulfillment
        # (progress capped at 2 with the surplus kill discarded), and the
        # planner still never writes by itself.
        self.assertTrue(effects)
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_upkeep_defeat_transitions_a_stage_exactly_once(self):
        accept_quest(self.player, self.two_stage.key)
        monster = self._monster("u-stage")
        effects = self._plan(self.player, [self._defeat_entry(self.player, monster)])
        self.assertTrue(effects)
        self.assertEqual(self._records()[0]["stage_index"], 0)

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_simulated_upkeep_defeat_grants_no_progress(self):
        accept_quest(self.player, self.tier_hunt.key)
        monster = self._monster("u-sim")
        effects = self._plan(
            self.player,
            [self._defeat_entry(self.player, monster, simulated=True)],
        )
        self.assertEqual(effects, [])
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_unattributed_upkeep_defeat_grants_no_progress(self):
        accept_quest(self.player, self.tier_hunt.key)
        monster = self._monster("u-anon")
        # An unattributed upkeep tick emits no defeat entries at all; the
        # planner sees an empty event set and plans nothing.
        effects = self._plan(self.player, [])
        self.assertEqual(effects, [])
        self.assertEqual(self._records()[0]["stage_progress"], 0)

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_simulated_upkeep_defeat_never_fails_a_protected_entity(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("u-guard")
        room = create_object(InstanceRoom, key="u-escort-room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        monster = self._monster("u-guard-killer")
        effects = self._plan(
            monster,
            [self._defeat_entry(monster, guard, simulated=True)],
        )
        self.assertEqual(effects, [])
        self.assertEqual(self._records()[0]["state"], QuestState.IN_PROGRESS.value)

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_attributed_upkeep_defeat_fails_a_protected_entity(self):
        record = accept_quest(self.player, self.escort_quest.key)
        guard = self._npc("u-guard-2")
        room = create_object(InstanceRoom, key="u-escort-room-2")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(guard,),
        )
        monster = self._monster("u-guard-killer-2")
        effects = self._plan(
            monster,
            [self._defeat_entry(monster, guard)],
        )
        # The planner stages the protected-entity failure transition (the
        # settlement commits it); the record itself stays untouched here.
        self.assertTrue(effects)
        self.assertEqual(self._records()[0]["state"], QuestState.IN_PROGRESS.value)
        self.assertEqual(
            self._records()[0]["protected_entity_ids"],
            [int(guard.pk)],
        )


if __name__ == "__main__":
    unittest.main()
