"""Slice of ``test_combat_session_flow``: the exploration opening's draft seed
and the encounter's durable opening-order policy.

An encounter-starting selection is one draft submission: it seeds the
initiating actor's entry and waits for every remaining required actor.
Interactive rounds -- overwhelming and solo ones included -- preserve the
selected commands and never dispatch autonomous compressed basic attacks. The
encounter's opening-order policy reorders the first complete round alone;
ordinary entry order never changes initiative.
"""
from tools.spec_traceability import covers_requirement
import contextlib
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.combat_initiation import initiate_field_combat
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    read_session,
    reconstruct_battlefield,
    submit_opening_action,
    submit_player_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.party import join_party
from world.rules.combat_session import _persist, from_storage, to_storage
from .._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    _race_key,
)
from ..combat_fixtures import grant_lineage


from ._support import (
    _T_CAST,
    _T_FOCUS,
    _open_scope,
)


def _dominant_player(key):
    """A player that dominates floor-tier monsters (overwhelming verdict)."""
    player = _player(key)
    for trait_key in ("atk_phys", "agility", "defense", "magic_power"):
        getattr(player.traits, trait_key).base = 200
    player.traits.hp.base = 2000
    player.traits.hp.current = 2000
    return player


def _entry_kinds(result):
    return [entry.kind for log in result.get("logs", ()) for entry in log.entries]


def _acting_actors(result):
    return [str(log.actor) for log in result.get("logs", ()) if log.entries]


class OpeningSeedTests(BattlefieldIsolation, EvenniaTestCase):
    """The opening is a draft seed: it waits, resolves one ordinary round, and
    never compresses for any verdict or target shape."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="seed arena")
        self.player = _dominant_player("seed duelist")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST, _T_FOCUS.key])

    @contextlib.contextmanager
    def _dice(self, value):
        patches = (
            patch("world.rules.combat.battlefield.roll_d100", return_value=value),
            patch("world.rules.combat.damage.roll_d100", return_value=value),
            patch("world.rules.combat.rounds.roll_d100", return_value=value),
            patch("world.rules.action.gates.roll_d100", return_value=value),
        )
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            yield

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_solo_opening_seeds_and_resolves_one_ordinary_round(self):
        monster = _monster("seeded wolf", hp=2000, atk=1)
        monster.location = self.room
        hp_before = int(monster.traits.hp.current)
        engage(self.player, monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            result = submit_opening_action(self.player, _T_FOCUS.key, [])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        # A zero-effect opening runs no action of its own, so the monster is
        # exactly where it started and no compressed follow-up attack touched
        # it: one ordinary round, one action per combatant.
        self.assertEqual(int(monster.traits.hp.current), hp_before)

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_player_overwhelming_opening_resolves_one_ordinary_round(self):
        weak = _monster("weak goblin", hp=100, atk=10)
        weak.location = self.room
        engage(self.player, weak)
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "party",
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            result = submit_opening_action(self.player, _T_CAST, [weak])
        self.assertIn(result["outcome"], ("round", "victory"))
        # Compression is what "one-shot settlement" would look like; the
        # ordinary round path never produces its summary entry.
        self.assertNotIn("overwhelm_resolution", _entry_kinds(result))

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_overwhelming_party_opening_waits_for_every_command(self):
        companion = create_object(NPC, key="seed companion", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        weak = _monster("waiting goblin", hp=100, atk=10)
        weak.location = self.room
        with self._dice(50):
            seeded = initiate_field_combat(self.player, _T_CAST, weak)
        # The overwhelming verdict did not compress: the initiating choice is
        # saved and the round waits for the companion's command.
        record = read_session(self.player)
        self.assertEqual(seeded["outcome"], "draft")
        self.assertEqual(classify_overwhelm(reconstruct_battlefield(self.player, record)), "party")
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(record.opening_first_actor, str(self.player.key))
        self.assertEqual(int(weak.traits.hp.current), 100)
        self.assertEqual(int(companion.traits.hp.current), companion.traits.hp.base)
        with self._dice(50):
            resolved = submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [weak],
                commanded_actor=companion,
            )
        # The companion's confirmation resolves exactly ONE ordinary round:
        # no autonomous basic attacks replace the party's choices.
        # (The single round kills the weak goblin, so the session settles.)
        self.assertEqual(resolved["rounds_elapsed"], 1)
        self.assertIn(resolved["outcome"], ("round", "victory"))
        self.assertIsNone(read_session(self.player))
        self.assertNotIn("overwhelm_resolution", _entry_kinds(resolved))

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_damaging_skill_at_only_an_ally_resolves_one_ordinary_round(self):
        weak = _monster("untouched", hp=500, atk=10)
        weak.location = self.room
        ally = _player("ally-only-target")
        ally.location = self.room
        engage(self.player, weak)
        _persist(
            self.player,
            from_storage(
                {
                    **to_storage(read_session(self.player)),
                    "player_ids": (self.player.pk, ally.pk),
                }
            ),
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            result = submit_opening_action(self.player, _T_CAST, [ally])
        self.assertIn(result["outcome"], ("round", "victory"))
        self.assertNotIn("overwhelm_resolution", _entry_kinds(result))
        self.assertEqual(int(weak.traits.hp.current), 500)
        self.assertLess(int(ally.traits.hp.current), ally.traits.hp.base)


class OpeningOrderPolicyTests(BattlefieldIsolation, EvenniaTestCase):
    """The encounter's opening-order policy reorders the first complete round
    only; an ordinary engagement never reorders anything."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="order arena")
        self.player = _player("ordered duelist")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.player.traits.agility.base = 40
        self.monster = _monster("quick foe", hp=2000, atk=10)
        self.monster.traits.agility.base = 100
        self.monster.location = self.room

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_opening_order_policy_applies_to_the_first_round_only(self):
        # The field initiation grants the initiator the first action; the
        # quicker monster still acts first once ordinary initiative governs.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            opening = initiate_field_combat(self.player, BASIC_ATTACK_KEY, self.monster)
        self.assertIn(opening["outcome"], ("round", "continue"))
        self.assertEqual(_acting_actors(opening)[0], str(self.player.key))
        self.assertIsNone(read_session(self.player).opening_first_actor)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            second = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        self.assertIn(second["outcome"], ("round", "continue", "victory", "defeat"))
        self.assertEqual(_acting_actors(second)[0], str(self.monster.key))

    @covers_requirement(
    "player-combat-session::interactive-encounter-openings-seed-a-draft-and-never-replace-party-choices-with-compression"
)
    def test_ordinary_entry_order_never_reorders_initiative(self):
        fast = _monster("first striker", hp=2000, atk=1)
        fast.traits.agility.base = 100
        fast.location = self.room
        engage(self.player, fast)
        self.assertIsNone(read_session(self.player).opening_first_actor)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=50), patch("world.rules.combat.damage.roll_d100", return_value=50), patch("world.rules.combat.rounds.roll_d100", return_value=50):
            result = submit_opening_action(self.player, BASIC_ATTACK_KEY, [fast])
        self.assertIn(result["outcome"], ("round", "continue"))
        self.assertEqual(_acting_actors(result)[0], str(fast.key))
