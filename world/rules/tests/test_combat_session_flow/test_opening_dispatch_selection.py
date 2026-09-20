"""Slice of ``test_combat_session_flow``: opening dispatch selection and
the compressed-opening first strike.
"""
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
from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from ..combat_fixtures import grant_lineage


from ._support import (
    _T_CAST,
    _T_FOCUS,
    _open_scope,
)


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
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.rounds.classify_overwhelm", return_value="foes"),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
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
            patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.rounds.roll_d100", return_value=50),
            patch("world.rules.action.gates.roll_d100", return_value=50),
            patch("world.rules.combat_session.rounds.classify_overwhelm", return_value=None),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
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
            patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.rounds.roll_d100", return_value=50),
            patch("world.rules.action.gates.roll_d100", return_value=50),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
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
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
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
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.combat_session.rounds.resolve_overwhelm", side_effect=spy),
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
