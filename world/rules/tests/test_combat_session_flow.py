"""Combat-session flow tests: innate skills, engagement, rounds, and seams."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.skills.handler import INNATE_SKILL_KEYS
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.registry import SKILL_REGISTRY, SkillKind, TargetSpec

from ._combat_session_helpers import (
    BattlefieldIsolation,
    SEAM_AREA_KEY,
    _monster,
    _player,
)
from .combat_fixtures import grant_lineage


class InnateSkillTests(EvenniaTest):
    @covers_requirement("universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data")
    def test_no_skill_entity_owns_both_innate_actions(self):
        player = _player()
        player.db.skills = None
        self.assertEqual(
            player.skills.owned_keys(),
            [
                "flee",
                "basic_attack",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )
        self.assertIn("basic_attack", INNATE_SKILL_KEYS)

    def test_full_import_list_plus_innate(self):
        player = _player()
        player.db.skills = {"active": ["fire_ball"], "passive": ["defense_instinct"]}
        self.assertEqual(
            player.skills.owned_keys(),
            [
                "fire_ball",
                "defense_instinct",
                "flee",
                "basic_attack",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )

    def test_monster_instance_can_fight_without_spawned_skills(self):
        monster = create_object(Monster, key="bare")
        monster.db.skills = None
        self.assertIn("basic_attack", monster.skills.owned_keys())

    def test_basic_attack_is_zero_cost_single_enemy_physical(self):
        skill = SKILL_REGISTRY["basic_attack"]
        self.assertEqual(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.target_spec, TargetSpec.SINGLE)
        self.assertEqual(skill.cost, {})
        self.assertFalse(skill.usable_out_of_combat)
        self.assertTrue(any(e.startswith("damage:") for e in skill.effects))

    def test_basic_attack_rejects_out_of_combat(self):
        player = _player()
        request = ActionRequest(
            player,
            "basic_attack",
            [player],
            __import__(
                "world.rules.targeting", fromlist=["RoomActionContext"]
            ).RoomActionContext(player.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)

class EngageTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="forest")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("goblin")
        self.monster.location = self.room

    def test_present_monster_can_be_engaged(self):
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].mode, "hostile")
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertTrue(is_in_active_session(self.player))

    def test_remote_or_dead_target_is_rejected(self):
        other_room = create_object(Room, key="other")
        remote = _monster("remote")
        remote.location = other_room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, remote)
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)

        dead = _monster("dead", hp=0)
        dead.location = self.room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, dead)
        self.assertEqual(ctx.exception.args[0], SessionReason.TARGET_DEAD)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    def test_active_session_blocks_another_engagement(self):
        engage(self.player, self.monster)
        second = _monster("second")
        second.location = self.room
        with self.assertRaises(CombatSessionError) as ctx:
            engage(self.player, second)
        self.assertEqual(ctx.exception.args[0], SessionReason.ALREADY_IN_COMBAT)

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_engage_alone_never_runs_a_round(self):
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)
        from world.rules.clock import get_world_clock

        self.assertEqual(get_world_clock().tick, 0)

class PlayerRoundTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        self.monster = _monster("goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::one-preflight-valid-player-action-drives-one-complete-ordinary-combat-round")
    def test_invalid_cast_preserves_round_before_initiative(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            result = submit_player_action(self.player, "no_such_skill", [self.monster])
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.UNKNOWN_SKILL)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    def test_one_request_drives_one_complete_round(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_mid_round_invalidation_consumes_round(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        # Whatever the outcome, the round count advanced exactly once.
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(result["rounds_elapsed"], 1)

    def test_flee_closes_the_same_session(self):
        engage(self.player, self.monster)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, "flee", [])
        self.assertEqual(result["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_terminal_victory_settles_rounds_once_and_clears(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    def test_no_action_before_overwhelm_round(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].rounds_elapsed, 0)
        self.assertEqual(self.monster.traits.hp.current, 100)

    def test_overwhelming_player_resolves_after_first_action(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)

class CommandedActionAttributionTests(BattlefieldIsolation, EvenniaTestCase):
    """overwhelm-log-attribution: the compressed log of a player-overwhelming
    session marks the player's commanded action and keeps every attack's own
    roll line, so a self-commanded basic attack can never be misread as the
    attack that damaged the enemy. Self-targeting damage stays legal: the
    commanded action resolves against the actor."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="attribution arena")
        self.player = _player("attribution player")
        self.player.location = self.room
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("attribution goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_commanded_self_attack_is_marked_and_rolls_stay_attributable(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=44):
            result = submit_player_action(
                self.player, "basic_attack", [self.player]
            )
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 2)
        # The self-commanded basic attack resolved against the actor (a miss
        # against the player's own agility), leaving the player unharmed.
        self.assertEqual(self.player.traits.hp.current, 2000)
        marker = "你施展了「基本攻擊」。"
        self_miss = (
            f"{self.player.key} 對 {self.player.key} 的攻擊擲出了 44。"
        )
        self.assertIn(marker, "\n".join(render_plain_text(log) for log in result["logs"]))
        commanded_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == "basic_attack"
            and str(log.targets[0]) == str(self.player.key)
        ]
        self.assertEqual(len(commanded_logs), 1)
        self.assertTrue(commanded_logs[0].startswith(marker))
        self.assertIn(self_miss, commanded_logs[0])
        # The compression's auto basic attack against the enemy keeps its own
        # roll line immediately before its damage line.
        auto_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == "basic_attack"
            and str(log.targets[0]) == str(self.monster.key)
        ]
        self.assertEqual(len(auto_logs), 1)
        auto_lines = auto_logs[0].splitlines()
        self.assertEqual(
            auto_lines[0],
            f"{self.player.key} 對 {self.monster.key} 的攻擊擲出了 44。",
        )
        self.assertTrue(
            auto_lines[1].startswith(
                f"{self.player.key} 對 {self.monster.key} 造成了 "
            )
        )

class RoundSettlementSeamTests(BattlefieldIsolation, EvenniaTestCase):
    """Cross-cutting regression tests for the shared round seam (task 3.2).

    One session flow exercises every seam phase in order -- a preflight
    rejection (no round), a reverse-overwhelm ordinary round, a friendly-fire
    penalty rollback on a failed terminal settlement, and the terminal
    settlement itself -- so later changes to ``submit_player_action``/
    ``settle_session`` cannot silently break the shared outer transaction.
    """

    def setUp(self):
        super().setUp()
        register_catalog()
        # Shipped ANY area skill; the player needs its 24 MP cost, set below.
        self.room = create_object(Room, key="seam arena")
        self.player = _player("seam player")
        self.player.location = self.room
        # wind_mastery keeps the 術師-tier wind_blade castable at the tuned
        # magic level 2 (the gate is satisfied by direct mastery, damage is
        # unaffected).
        self.player.db.skills = {
            "active": [SEAM_AREA_KEY],
            "passive": ["wind_mastery"],
        }
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 2
        self.player.traits.hp.base = 390
        self.player.traits.hp.current = 390
        self.companion = create_object(NPC, key="誤傷夥伴", location=self.room)
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.companion.traits, key).base = 2
        self.companion.traits.hp.base = 100
        self.companion.traits.hp.current = 100
        join_party(self.companion, self.player)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            self.companion, self.player, AffinitySource.QUEST_COMPLETION, 10
        )
        # Foe team overwhelming by the power-ratio rule alone (>= 100x):
        # power = stat sum x hp = (200+30+100) x 1300 = 429000 vs player team
        # 3920, with a <= 5-round estimate (198 base damage at a 0.78 hit
        # rate). Monster magic_power is a static trait pinned to the (0, 0)
        # band, so the
        # attack/agility/defense carry the power. The monster's d100 margin
        # (77) stays below the critical threshold: its solid hit lands for
        # 298 damage, flooring the companion but leaving the player standing.
        self.monster = create_object(Monster, key="seam goblin")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        for key, value in {
            "atk_phys": 200,
            "agility": 30,
            "defense": 100,
        }.items():
            getattr(self.monster.traits, key).base = value
        self.monster.traits.hp.base = 1300
        self.monster.traits.hp.current = 1300
        self.monster.location = self.room

    def tearDown(self):

        super().tearDown()

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_one_session_flow_covers_all_seam_phases(self):
        engage(self.player, self.monster)
        from world.rules.overwhelm import classify_overwhelm

        # Reverse overwhelm: the FOE team is the overwhelming one, so the
        # player's action runs one ordinary round, never the compression.
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "foes",
        )
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            # 1. A preflight rejection consumes no round and no world time.
            result = submit_player_action(
                self.player, "no_such_skill", [self.monster]
            )
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(read_session(self.player).rounds_elapsed, 0)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1300)

            # 2. The reverse-overwhelm action drives one ordinary round: the
            #    monster's solid hit floors the companion nonlethally, and
            #    the player's area attack hits both the monster and the
            #    companion, so the friendly-fire penalty applies (-1 per hit)
            #    inside the seam.
            with patch("world.rules.combat.roll_d100", return_value=100):
                result = submit_player_action(
                    self.player,
                    SEAM_AREA_KEY,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "round")
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)
            self.assertEqual(self.companion.traits.hp.current, 1)

            # 3. A terminal settlement failure rolls the round back,
            #    including the fresh friendly-fire penalty (party/relations
            #    surfaces are restored with the round). The player's attack
            #    kills the pinned monster, so the settlement step runs and
            #    fails; the monster is held from fleeing so the round stays
            #    on the kill path.
            self.monster.traits.hp.current = 1
            with (
                patch("world.rules.combat.roll_d100", return_value=100),
                patch(
                    "world.rules.combat_session.settle_combat_result",
                    side_effect=RuntimeError("clock write failed"),
                ),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
            ):
                with self.assertRaises(RuntimeError):
                    submit_player_action(
                        self.player,
                        SEAM_AREA_KEY,
                        [self.monster, self.companion],
                    )
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)

            # 4. A player-defeat round settles exactly once and clears the
            #    session: the monster's solid hit floors the weakened player
            #    on its initiative turn. Both elapsed rounds settle (12 s).
            self.player.traits.hp.current = 40
            with (
                patch("world.rules.combat.roll_d100", return_value=100),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
            ):
                result = submit_player_action(
                    self.player,
                    SEAM_AREA_KEY,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "defeat")
            self.assertEqual(clock.tick, 12)
            self.assertIsNone(self.player.db.active_combat)
            self.assertFalse(is_in_active_session(self.player))

class CommandSessionTests(BattlefieldIsolation, QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1 = create_object(Room, key="cmd arena")
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.monster = _monster("cmd goblin")
        self.monster.location = self.room1

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_active_session_cast_does_not_advance_command_time(self):
        from world.rules.combat_session import engage

        grant_lineage(self.char1, ["fire_ball"])
        engage(self.char1, self.monster)
        clock = WorldClock()
        with patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), "fire_ball=cmd goblin", None)
        self.assertEqual(clock.tick, 0)
