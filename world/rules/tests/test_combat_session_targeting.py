"""Explicit-target facade contract tests for combat sessions."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.clock import WorldClock
from world.rules.action import RejectReason
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    from_storage,
    read_session,
    submit_player_action,
)
from world.rules.disengage import FLEE_SKILL_KEY
from world.tests.synthetic_data import SYNTH_SKILLS

from ._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import grant_lineage

# Synthetic vehicles for the facade (test-data-independence): ANY-faction
# single-target and AREA damage skills carry the same resolver semantics the
# submitted skill keys used to.
_T_ANY_SINGLE = SYNTH_SKILLS["t_ember_burst"].key
_T_ANY_AREA = SYNTH_SEAM_AREA_SKILL.key


def _scope_extra():
    skills = dict(synth_innate_overlay()["skills"])
    skills[SYNTH_SEAM_AREA_SKILL.key] = SYNTH_SEAM_AREA_SKILL
    return {"skills": skills}


class ExplicitTargetContractTests(BattlefieldIsolation, EvenniaTestCase):
    """Regression tests for the explicit-list facade contract (tasks 2.2-2.3)."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            "monster_tiers",
            extra=_scope_extra(),
        )
        super().setUp()
        self.room = create_object(Room, key="explicit arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, [_T_ANY_AREA, _T_ANY_SINGLE])
        self.monster_a = _monster("alpha", hp=100)
        self.monster_b = _monster("beta", hp=100)
        self.monster_a.location = self.room
        self.monster_b.location = self.room

    @covers_requirement(
        "player-combat-session::player-combat-submission-accepts-one-explicit-target-value"
    )
    def test_explicit_area_targets_drive_one_round(self):
        engage(self.player, self.monster_a)
        record = read_session(self.player)
        from world.rules.combat_session import to_storage

        record = from_storage(
            {
                **to_storage(record),
                "enemy_ids": [self.monster_a.pk, self.monster_b.pk],
            }
        )
        from world.rules.combat_session import _persist

        _persist(self.player, record)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_ANY_AREA, [self.monster_a, self.monster_b]
            )
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_approved_shorthand_reaches_ordinary_targeting(self):
        engage(self.player, self.monster_a)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_ANY_AREA, "all-enemies")
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertLessEqual(self.monster_a.traits.hp.current, 99)
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_duplicate_explicit_target_rejects_before_initiative(self):
        engage(self.player, self.monster_a)
        clock = WorldClock()
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.combat.roll_d100") as roll,
        ):
            result = submit_player_action(
                self.player, _T_ANY_AREA, [self.monster_a, self.monster_a]
            )
        roll.assert_not_called()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.TARGET_SPEC_MISMATCH)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    def test_remote_participant_rejects_before_initiative(self):
        engage(self.player, self.monster_a)
        other_room = create_object(Room, key="remote")
        remote = _monster("remote", hp=50)
        remote.location = other_room
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            with self.assertRaises(CombatSessionError) as ctx:
                submit_player_action(
                    self.player, _T_ANY_SINGLE, [self.monster_a, remote]
                )
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    def test_ally_is_a_valid_target_for_any_skill(self):
        engage(self.player, self.monster_a)
        ally = _player("ally")
        ally.location = self.room
        from world.rules.combat_session import to_storage

        record = from_storage(
            {
                **to_storage(read_session(self.player)),
                "player_ids": (self.player.pk, ally.pk),
            }
        )
        from world.rules.combat_session import _persist

        _persist(self.player, record)
        # Freely-targetable (ANY) skills accept an ally as an explicit target;
        # the round resolves and the ally takes the damage instead of the
        # faction check rejecting it (friendly-fire reachability).
        result = submit_player_action(self.player, _T_ANY_SINGLE, [ally])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_old_single_object_input_is_rejected(self):
        engage(self.player, self.monster_a)
        with self.assertRaises(TypeError):
            submit_player_action(self.player, _T_ANY_SINGLE, self.monster_a)

    def test_self_facade_requires_empty_list(self):
        engage(self.player, self.monster_a)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = submit_player_action(self.player, FLEE_SKILL_KEY, [])
        self.assertEqual(result["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)
