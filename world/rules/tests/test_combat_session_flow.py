"""Combat-session flow tests: innate skills, engagement, rounds, and seams."""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from dataclasses import replace
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
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

from ._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import grant_lineage

SEAM_AREA_KEY = SYNTH_SEAM_AREA_SKILL.key
_T_CAST = SYNTH_SKILLS["t_ember_burst"].key
_T_PASSIVE = SYNTH_SKILLS["t_steady_stride"].key
# Non-damaging zero-cost active with no targets: the round-path opener and
# the first-strike carrier (the shipped concentrate analogue).
_T_FOCUS = make_skill(
    "t_still_breath", label="靜息", effects=[], target_spec=TargetSpec.NONE
)
# The same AREA template at zero MP cost for the 2-MP seam casters.
_T_SEAM_CASCADE = replace(SYNTH_SEAM_AREA_SKILL, cost={})


def _innate_keys():
    """The innate roster from the (patched) live surfaces, never a literal."""
    attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    flee_key = _live_registry("world.rules.disengage", "FLEE_SKILL_KEY")
    innate = _live_registry("world.skills.handler", "INNATE_SKILL_KEYS")
    act_registry = _live_registry("world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY")
    unlock_free = sorted(key for key, act in act_registry.items() if not act.unlock)
    return attack_key, flee_key, innate, unlock_free


def _live_registry(dotted: str, attribute: str):
    import importlib

    return getattr(importlib.import_module(dotted), attribute)


def _open_scope(test, *, monster_tiers=True, **extra_skills):
    skills = dict(synth_innate_overlay()["skills"])
    skills[SYNTH_SEAM_AREA_SKILL.key] = SYNTH_SEAM_AREA_SKILL
    skills[_T_SEAM_CASCADE.key] = _T_SEAM_CASCADE
    skills[_T_FOCUS.key] = _T_FOCUS
    skills.update(extra_skills)
    logicals = ["skills", "elements", "sexual_acts", "races", "subraces", "static_tiers"]
    if monster_tiers:
        logicals.append("monster_tiers")
    open_synthetic_scope(
        test,
        *logicals,
        extra={"skills": skills},
    )


def _basic_attack_row():
    """The innate attack row as the patched registry serves it."""
    attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    registry = _live_registry("world.skills.registry", "SKILL_REGISTRY")
    return registry[attack_key]

class InnateSkillTests(EvenniaTest):
    def setUp(self):
        _open_scope(self)
        super().setUp()

    @covers_requirement("universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data")
    def test_no_skill_entity_owns_both_innate_actions(self):
        attack_key, flee_key, innate, unlock_free = _innate_keys()
        player = _player()
        player.db.skills = None
        self.assertEqual(
            player.skills.owned_keys(),
            [
                flee_key,
                attack_key,
                *unlock_free,
            ],
        )
        self.assertIn(attack_key, innate)

    def test_full_import_list_plus_innate(self):
        attack_key, flee_key, _, unlock_free = _innate_keys()
        player = _player()
        player.db.skills = {"active": [_T_CAST], "passive": [_T_PASSIVE]}
        self.assertEqual(
            player.skills.owned_keys(),
            [
                _T_CAST,
                _T_PASSIVE,
                flee_key,
                attack_key,
                *unlock_free,
            ],
        )

    def test_monster_instance_can_fight_without_spawned_skills(self):
        attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
        monster = create_object(Monster, key="bare")
        monster.db.skills = None
        self.assertIn(attack_key, monster.skills.owned_keys())

    def test_basic_attack_is_zero_cost_single_enemy_physical(self):
        skill = _basic_attack_row()
        self.assertEqual(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.target_spec, TargetSpec.SINGLE)
        self.assertEqual(skill.cost, {})
        # D-7 (field-combat initiation): the flag governs SELECTION only, so
        # the innate attack is selectable from exploration as the field-combat
        # initiation; the damaging-action gate keeps it unable to resolve
        # without a battlefield.
        self.assertTrue(skill.usable_out_of_combat)
        self.assertTrue(any(e.startswith("damage:") for e in skill.effects))

    @covers_requirement(
        "universal-action-ownership::innate-skill-keys-makes-flee-and-basic-attack-ownable-by-every-livingentity-regardless-of-import-or-spawn-data"
    )
    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_basic_attack_selectable_out_of_combat_but_damage_gated(self):
        player = _player()
        player.location = create_object(Room, key="bare room")
        mp_before = player.traits.mp.value
        hp_before = player.traits.hp.value
        request = ActionRequest(
            player,
            BASIC_ATTACK_KEY,
            [player],
            __import__(
                "world.rules.targeting", fromlist=["RoomActionContext"]
            ).RoomActionContext(player.location),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        # The usable_out_of_combat gate no longer rejects it (it is
        # deliberately selectable outside combat); the damaging-action gate
        # rejects instead, before any resource or damage step.
        self.assertEqual(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertEqual(player.traits.mp.value, mp_before)
        self.assertEqual(player.traits.hp.value, hp_before)

class EngageTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        _open_scope(self)
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
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
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
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_mid_round_invalidation_consumes_round(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
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
            result = submit_player_action(self.player, _T_CAST, [self.monster])
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

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    def test_overwhelming_player_resolves_after_first_action(self):
        # combat-session-opening-dispatch: an in-session submission under a
        # player-overwhelming verdict resolves exactly one ordinary round and
        # never dispatches the compressed resolver. The synthetic cast kills the
        # weak monster inside that single round, so the session still settles
        # as a victory -- but through one round, not compression.
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, self.monster)
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError(
                    "an in-session submission must never dispatch compression"
                ),
            ) as resolver,
        ):
            result = submit_player_action(self.player, _T_CAST, [self.monster])
        resolver.assert_not_called()
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertIsNone(self.player.db.active_combat)

class CommandedActionAttributionTests(BattlefieldIsolation, EvenniaTestCase):
    """overwhelm-log-attribution under the opening seam: the compressed log of
    a player-overwhelming session opened through ``submit_opening_action()``
    marks the player's commanded skill exactly once and keeps that attack's
    own roll line, so the marker can never be misread as a different action.
    (combat-session-opening-dispatch 5.7/5.12: compression is now reachable
    only through the opening seam, so the attribution contract is driven
    there.)"""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="attribution arena")
        self.player = _player("attribution player")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("attribution goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_compressed_opening_marks_commanded_skill_once_with_attributable_rolls(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=44):
            result = submit_opening_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        # Exactly one first-round commanded_action marker, kind skill, the
        # submitted key's label, attached to the player's own cast log.
        markers = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "commanded_action"
        ]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].actor, str(self.player.key))
        self.assertEqual(markers[0].data, {"skill": SYNTH_SKILLS[_T_CAST].label})
        opening_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == _T_CAST
        ]
        self.assertEqual(len(opening_logs), 1)
        opening_lines = opening_logs[0].splitlines()
        # The marker prefixes the action's own roll line, which stays
        # immediately before the damage it describes.
        self.assertEqual(opening_lines[0], f"你施展了「{SYNTH_SKILLS[_T_CAST].label}」。")
        self.assertEqual(
            opening_lines[1],
            f"{self.player.key} 對 {self.monster.key} 的攻擊擲出了 44。",
        )
        self.assertTrue(
            opening_lines[2].startswith(
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
        _open_scope(self, monster_tiers=False)
        super().setUp()
        register_catalog()
        # ANY-faction synthetic area skill (zero cost, so the deliberately
        # weak seam caster can still pay for it).
        self.room = create_object(Room, key="seam arena")
        self.player = _player("seam player")
        self.player.location = self.room
        self.player.db.skills = {
            "active": [_T_SEAM_CASCADE.key],
            "passive": [],
        }
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 2
        self.player.traits.hp.base = 390
        self.player.traits.hp.current = 390
        self.companion = create_object(NPC, key="誤傷夥伴", location=self.room)
        self.companion.race = _race_key()
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
                    _T_SEAM_CASCADE.key,
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
                        _T_SEAM_CASCADE.key,
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
            settled: list[int] = []
            from world.rules.combat_session import settle_combat_result as real_settle

            def spy(result_, entities_):
                settled.append(result_.total_seconds)
                return real_settle(result_, entities_)

            with (
                patch("world.rules.combat.roll_d100", return_value=100),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
                patch(
                    "world.rules.combat_session.settle_combat_result",
                    side_effect=spy,
                ),
            ):
                result = submit_player_action(
                    self.player,
                    _T_SEAM_CASCADE.key,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "defeat")
            # The round-time settlement ran exactly once for exactly 12 s.
            # The defeat aftermath's recovery advance (defeat-aftermath-
            # recovery) is a further, separately priced advance, so the
            # final tick is the 12 s settle plus that fixture-priced window.
            self.assertEqual(settled, [12])
            self.assertGreaterEqual(clock.tick, 12)
            self.assertIsNone(self.player.db.active_combat)
            self.assertFalse(is_in_active_session(self.player))

class CommandSessionTests(BattlefieldIsolation, QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room1 = create_object(Room, key="cmd arena")
        self.char1.location = self.room1
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        self.monster = _monster("cmd goblin")
        self.monster.location = self.room1

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_active_session_cast_does_not_advance_command_time(self):
        from world.rules.combat_session import engage

        grant_lineage(self.char1, [_T_CAST])
        engage(self.char1, self.monster)
        clock = WorldClock()
        with patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), f"{_T_CAST}=cmd goblin", None)
        self.assertEqual(clock.tick, 0)


class EngageGroupTests(BattlefieldIsolation, EvenniaTestCase):
    """combat-session-opening-dispatch 5.9/5.10/5.13: group engagement."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="group arena")
        self.player = _player("group hunter")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_engage_group_opens_one_session_and_resolves_to_victory(self):
        m1 = _monster("m1", hp=100, atk=10)
        m2 = _monster("m2", hp=100, atk=10)
        m1.location = self.room
        m2.location = self.room
        result = engage_group(self.player, [m2, m1])
        record = result["record"]
        self.assertEqual(record.enemy_ids, tuple(sorted([int(m1.pk), int(m2.pk)])))
        battlefield = reconstruct_battlefield(self.player, record)
        self.assertEqual(
            sorted(str(k) for k in battlefield.teams["foes"]),
            sorted([m1.key, m2.key]),
        )
        # The player dominates both floor-tier foes, so the opening's
        # two-part judgement selects compression, and the round-1 cast
        # plus the auto-attacks settle the whole session in one call.
        with patch("world.rules.combat.roll_d100", return_value=100):
            outcome = submit_opening_action(self.player, _T_CAST, [m1])
        self.assertEqual(outcome["outcome"], "victory")
        self.assertGreaterEqual(
            len([
                entry
                for log in outcome["logs"]
                for entry in log.entries
                if entry.kind == "commanded_action"
            ]),
            1,
        )
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_engage_group_rejections_leave_no_session(self):
        from world.rules.clock import get_world_clock

        good = _monster("good", hp=100, atk=10)
        good.location = self.room
        dead = _monster("dead", hp=0)
        dead.location = self.room
        remote = _monster("remote", hp=100)
        remote.location = create_object(Room, key="elsewhere")
        stranger = create_object(NPC, key="npc-stranger", location=self.room)
        cases = [
            ([good, dead], SessionReason.TARGET_DEAD),
            ([good, remote], SessionReason.NOT_PRESENT),
            ([good, stranger], SessionReason.NOT_HOSTILE),
            ([good, good], SessionReason.DUPLICATE_PARTICIPANT),
            ([], SessionReason.MALFORMED_SESSION),
        ]
        for targets, reason in cases:
            with self.subTest(reason=reason), self.assertRaises(CombatSessionError) as ctx:
                engage_group(self.player, targets)
            self.assertEqual(ctx.exception.args[0], reason)
            self.assertIsNone(read_session(self.player))
        self.assertEqual(get_world_clock().tick, 0)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_opening_rejects_shorthand_and_off_roster_before_anything(self):
        m1 = _monster("opening foe", hp=100, atk=10)
        m1.location = self.room
        away = _monster("away foe", hp=100)
        away.location = create_object(Room, key="not here")
        engage_group(self.player, [m1])
        mp_before = self.player.traits.mp.value
        with self.assertRaises(TypeError):
            submit_opening_action(self.player, _T_CAST, "all-enemies")
        with self.assertRaises(CombatSessionError) as ctx:
            submit_opening_action(self.player, _T_CAST, [away])
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)
        record = read_session(self.player)
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.player.traits.mp.value, mp_before)

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_two_enemy_session_exercises_scans_knockouts_and_settlement(self):
        # 5.11: a two-enemy session through _primary_opponent_id(), the
        # friendly-fire scan, nonlethal knockout, and terminal settlement.
        import world.rules.combat_session as session_mod

        companion = create_object(NPC, key="並肩", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        m1 = _monster("twin a", hp=100, atk=10)
        m2 = _monster("twin b", hp=100, atk=10)
        m1.location = self.room
        m2.location = self.room
        grant_lineage(self.player, [SYNTH_SEAM_AREA_SKILL.key])
        engage_group(self.player, [m1, m2])
        seen: list = []
        real_primary = session_mod._primary_opponent_id

        def spy(battlefield, record):
            value = real_primary(battlefield, record)
            seen.append(value)
            return value

        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.action.roll_d100", return_value=100),
            patch.object(session_mod, "_primary_opponent_id", side_effect=spy),
        ):
            result = submit_opening_action(self.player, SYNTH_SEAM_AREA_SKILL.key, [m1])
        self.assertGreaterEqual(len(seen), 1)
        self.assertEqual(
            seen[0], min(int(m1.pk), int(m2.pk))
        )
        self.assertEqual(result["outcome"], "victory")
        # The AREA cast hit the companion through the two-enemy
        # roster and the nonlethal companion policy floored it at 1 HP; the
        # per-hit affinity penalty contract itself is pinned in
        # test_friendly_fire (here the scan simply must not crash the flow).
        # The player's AREA cast reached the companion through the
        # two-enemy roster (observed: one 7-damage hit under the patched
        # rolls); the friendly-fire/coercion scans ran over the two-enemy
        # logs without crashing the flow. The per-hit affinity-penalty
        # contract itself is pinned in test_friendly_fire.
        self.assertLess(companion.traits.hp.current, companion.traits.hp.max)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    def test_both_openings_forward_the_same_policy_kwargs(self):
        # 5.4: the round and overwhelm entries receive the identical
        # simulated/nonlethal/journal/notification policy.
        from world.rules.combat import run_round as real_run_round
        from world.rules.overwhelm import resolve_overwhelm as real_resolve

        companion = create_object(NPC, key="政策護伴", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        captured = {}

        def record_round(field, provider, **kwargs):
            captured.setdefault("round", kwargs)
            return real_run_round(field, provider, **kwargs)

        def record_resolve(field, provider, **kwargs):
            captured.setdefault("overwhelm", kwargs)
            return real_resolve(field, provider, **kwargs)

        def build():
            foe = _monster("政策敵", hp=300, atk=10)
            foe.location = self.room
            engage(self.player, foe)
            return foe

        with (
            patch("world.rules.combat.roll_d100", return_value=44),
            patch("world.rules.action.roll_d100", return_value=44),
            patch("world.rules.combat_session.run_round", side_effect=record_round),
        ):
            submit_player_action(self.player, _T_CAST, [build()])
        self.player.db.active_combat = None
        with (
            patch("world.rules.combat.roll_d100", return_value=44),
            patch("world.rules.action.roll_d100", return_value=44),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=record_resolve,
            ),
        ):
            submit_opening_action(self.player, _T_CAST, [build()])
        self.assertEqual(
            sorted(captured), ["overwhelm", "round"]
        )
        for key in ("simulated", "nonlethal_keys"):
            self.assertEqual(
                captured["round"][key], captured["overwhelm"][key], key
            )
        self.assertFalse(captured["round"]["simulated"])
        self.assertEqual(
            captured["round"]["nonlethal_keys"], {companion.key}
        )
        for key in ("journal_sink", "notifications_sink"):
            self.assertIsInstance(captured["round"][key], list, key)
            self.assertIsInstance(captured["overwhelm"][key], list, key)


class OpeningDispatchSelectionTests(BattlefieldIsolation, EvenniaTestCase):
    """combat-session-opening-dispatch 5.5/5.6: two-part dispatch + first strike."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="dispatch arena")
        self.player = _player("dispatch duelist")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST, _T_FOCUS.key])
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_non_damaging_skill_under_player_verdict_takes_the_round_path(self):
        weak = _monster("weak", hp=100, atk=10)
        weak.location = self.room
        engage(self.player, weak)
        self.assertEqual(
            classify_overwhelm(reconstruct_battlefield(self.player, read_session(self.player))),
            "party",
        )
        result = submit_opening_action(self.player, _T_FOCUS.key, [])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(weak.traits.hp.current, 100)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_foe_verdict_opening_takes_the_round_path(self):
        weak = _monster("weak", hp=100, atk=10)
        weak.location = self.room
        engage(self.player, weak)
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("world.rules.combat_session.classify_overwhelm", return_value="foes"),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError(
                    "a foe-direction verdict must never compress"
                ),
            ) as resolver,
        ):
            result = submit_opening_action(self.player, _T_CAST, [weak])
        resolver.assert_not_called()
        # One ordinary round resolved the (patched) verdict fight; whether it
        # settled depends on the single round's damage, never on compression.
        self.assertIn(result["outcome"], ("round", "victory"))
        if result["outcome"] == "round":
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_contested_verdict_opening_takes_the_round_path(self):
        # 5.5 / contested-verdict scenario: a None verdict is ineligible even
        # for a damaging skill, and must not reach the resolver.
        weak = _monster("weak", hp=500, atk=10)
        weak.location = self.room
        engage(self.player, weak)
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.action.roll_d100", return_value=50),
            patch("world.rules.combat_session.classify_overwhelm", return_value=None),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError("a contested verdict must never compress"),
            ) as resolver,
        ):
            result = submit_opening_action(self.player, _T_CAST, [weak])
        resolver.assert_not_called()
        self.assertIn(result["outcome"], ("round", "victory"))
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed if read_session(self.player) else 1, 1)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_damaging_skill_at_only_an_ally_does_not_compress(self):
        # 5.5 / damaging-away-from-enemy gate: a DamageEffect skill whose
        # submitted targets never name an enemy fails the predicate even under
        # a player-direction verdict, resolving one ordinary round instead.
        weak = _monster("untouched", hp=500, atk=10)
        weak.location = self.room
        ally = _player("ally-only-target")
        ally.location = self.room
        engage(self.player, weak)
        from world.rules.combat_session import _persist, from_storage, to_storage

        _persist(
            self.player,
            from_storage(
                {
                    **to_storage(read_session(self.player)),
                    "player_ids": (self.player.pk, ally.pk),
                }
            ),
        )
        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.action.roll_d100", return_value=50),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError(
                    "a skill aimed away from every enemy must never compress"
                ),
            ),
        ):
            result = submit_opening_action(self.player, _T_CAST, [ally])
        self.assertIn(result["outcome"], ("round", "victory"))
        self.assertEqual(weak.traits.hp.current, 500)
        record = read_session(self.player)
        self.assertEqual(record.rounds_elapsed if record else 1, 1)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_opening_grants_the_player_the_first_turn_regardless_of_initiative(self):
        fast = _monster("fast foe", hp=400, atk=10)
        fast.traits.agility.base = 100
        fast.location = self.room
        self.player.traits.agility.base = 40
        engage(self.player, fast)
        # The non-damaging focus never damages, so the opening takes the round path;
        # first_actor must still move the player to the head of the round.
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = submit_opening_action(self.player, _T_FOCUS.key, [])
        self.assertEqual(result["outcome"], "round")
        acting_logs = [log for log in result["logs"] if log.entries]
        self.assertEqual(str(acting_logs[0].actor), str(self.player.key))
        actors = [str(log.actor) for log in acting_logs]
        self.assertIn(str(fast.key), actors)
        self.assertGreater(actors.index(str(fast.key)), actors.index(str(self.player.key)))
        # The monster acted after the player and hit it (roll 50 lands).
        self.assertLess(self.player.traits.hp.current, 2000)


class CompressedOpeningFirstStrikeTests(BattlefieldIsolation, EvenniaTestCase):
    """combat-session-opening-dispatch 5.6 under the compression selection:
    ``first_actor`` must reach ``resolve_overwhelm()``'s first round, not just
    ``run_round()``'s — a regression dropping the override only from the
    compressed branch would let the faster monster act before the opening."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="compressed arena")
        self.player = _player("compressed first strike")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        self.player.traits.atk_phys.base = 200
        self.player.traits.agility.base = 100
        self.player.traits.defense.base = 200
        self.player.traits.magic_power.base = 50
        self.player.traits.hp.base = 20000
        self.player.traits.hp.current = 20000
        # The monster out-agilities the player, so ordinary initiative would
        # place it first; only the first_actor override can reorder it.
        self.monster = _monster("quick goblin", hp=300)
        self.monster.traits.agility.base = 110
        self.monster.location = self.room

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_compressed_opening_forwards_first_actor_and_acts_first(self):
        import world.rules.overwhelm as overwhelm_mod

        engage(self.player, self.monster)
        self.assertEqual(
            classify_overwhelm(reconstruct_battlefield(self.player, read_session(self.player))),
            "party",
        )
        captured = {}
        real_resolve = overwhelm_mod.resolve_overwhelm

        def spy(field, provider, **kwargs):
            captured.update(kwargs)
            return real_resolve(field, provider, **kwargs)

        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.combat_session.resolve_overwhelm", side_effect=spy),
        ):
                result = submit_opening_action(self.player, _T_CAST, [self.monster])
        # The opening really compressed, and the override reached the resolver.
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(captured.get("first_actor"), str(self.player.key))
        # Ordinary initiative would have placed the quicker monster first; the
        # player's is nonetheless the first combatant action of the encounter.
        actors = [
            str(log.actor)
            for log in result["logs"]
            if log.entries and str(log.actor) in (str(self.player.key), str(self.monster.key))
        ]
        self.assertEqual(actors[0], str(self.player.key))
        self.assertIn(str(self.monster.key), actors)


class SubmissionStructuralTests(unittest.TestCase):
    """combat-session-opening-dispatch 5.3/5.8: structural tripwires."""

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    def test_in_session_entries_never_request_or_judge_compression(self):
        import ast as _ast

        import world.rules.combat_session as session

        for func in (session.submit_player_action, session.submit_player_item_use):
            tree = _ast.parse(inspect.getsource(func))
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Call):
                    self.assertNotIn(
                        "opening",
                        [kw.arg for kw in node.keywords if kw.arg],
                        func.__name__,
                    )
                    callee = node.func
                    name = callee.id if isinstance(callee, _ast.Name) else getattr(callee, "attr", "")
                    self.assertNotEqual(name, "classify_overwhelm", func.__name__)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_resolve_overwhelm_has_a_single_production_call_site(self):
        import ast as _ast

        root = Path(__file__).resolve().parents[3]
        callers = []
        for directory in ("commands", "typeclasses", "world"):
            for path in (root / directory).rglob("*.py"):
                if "tests" in path.parts:
                    continue
                tree = _ast.parse(path.read_text(encoding="utf-8"))
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.Call):
                        callee = node.func
                        name = callee.id if isinstance(callee, _ast.Name) else getattr(callee, "attr", "")
                        if name == "resolve_overwhelm":
                            callers.append(path)
        session_file = (root / "world" / "rules" / "combat_session.py").resolve()
        self.assertEqual([p.resolve() for p in callers], [session_file])
