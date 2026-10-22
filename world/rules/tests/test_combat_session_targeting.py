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
    engagement_base,
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
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_ANY_AREA, [self.monster_a, self.monster_b]
            )
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_approved_shorthand_reaches_ordinary_targeting(self):
        engage(self.player, self.monster_a)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(self.player, _T_ANY_AREA, "all-enemies")
        self.assertIn(result["outcome"], ("round", "victory", "defeat"))
        self.assertLessEqual(self.monster_a.traits.hp.current, 99)
        self.assertGreaterEqual(read_session(self.player).rounds_elapsed, 1)

    def test_duplicate_explicit_target_rejects_before_initiative(self):
        engage(self.player, self.monster_a)
        clock = WorldClock()
        with (
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.combat.battlefield.roll_d100") as roll,
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

    def test_self_flee_is_refused_by_the_facade(self):
        # The allied flee selection is the confirmed party exit now (§6), so
        # the facade refuses it outright: no individual escape resolves and
        # the session stays exactly where it was.
        engage(self.player, self.monster_a)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            with self.assertRaises(CombatSessionError) as ctx:
                submit_player_action(self.player, FLEE_SKILL_KEY, [])
        self.assertEqual(ctx.exception.args[0], "personal_flee_forbidden")
        self.assertIsNotNone(self.player.db.active_combat)


class SleepingRosterCases(BattlefieldIsolation, EvenniaTestCase):
    """Delta: sleep keeps presence and authority while excluding its commands."""

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
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        self.room = create_object(Room, key="sleeping roster arena")
        self.player = _player()
        self.player.location = self.room
        self.companion = create_object(
            NPC, key="awake companion", location=self.room
        )
        self.companion.race = self.player.race
        self.companion.apply_race_baseline()
        self.companion.traits.hp.base = 100
        self.companion.traits.hp.current = 100
        self.companion.traits.mp.base = 50
        self.companion.traits.mp.current = 50
        join_party(self.companion, self.player)
        grant_lineage(self.companion, [_T_ANY_SINGLE])
        self.monster = _monster("sleeping goblin", hp=500)
        self.monster.location = self.room

    @covers_requirement(
        "player-combat-session::commander-may-select-only-currently-controllable-allied-actors"
    )
    @covers_requirement(
        "player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership"
    )
    @covers_requirement(
        "player-combat-session::sleeping-roster-members-remain-present-without-commands"
    )
    def test_sleeping_commander_keeps_ownership_but_no_command_of_any_kind(self):
        from world.rules.combat_session import (
            _persist,
            confirm_actor_command,
            get_required_combat_actors,
            reconstruct_battlefield,
            submit_player_item_use,
            to_storage,
        )
        from world.rules.fatigue import SleepPosture, write_fatigue_state

        write_fatigue_state(self.player, 0, SleepPosture.FORCED)
        engage(self.player, self.monster)
        record = read_session(self.player)

        self.assertEqual(record.player_ids[0], self.player.pk)
        self.assertIsNotNone(read_session(self.player))
        self.assertIsNone(read_session(self.companion))
        self.assertEqual(record.initial_sleep_ids, (int(self.player.pk),))
        self.assertNotIn(int(self.player.pk), record.knocked_out_ids)
        field = reconstruct_battlefield(self.player, record)
        self.assertIn(str(self.player.key), field.roster)
        self.assertTrue(field.is_eligible(str(self.player.key)))
        required = set(get_required_combat_actors(record, field))
        self.assertNotIn(int(self.player.pk), required)
        self.assertIn(int(self.companion.pk), required)

        cases = (
            lambda: submit_player_action(
                self.player, _T_ANY_SINGLE, [self.monster]
            ),
            lambda: submit_player_item_use(self.player, "t_moss_tonic"),
            lambda: confirm_actor_command(
                self.player,
                record.session_id,
                0,
                0,
                self.player.pk,
                {
                    "kind": "tactical",
                    "payload": {"tactical_key": "defend", "target_id": None},
                },
            ),
        )
        for case in cases:
            with self.assertRaises(CombatSessionError) as caught:
                case()
            self.assertEqual(
                caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR
            )
        unchanged = read_session(self.player)
        self.assertEqual(unchanged.draft_entries, {})
        self.assertEqual(unchanged.draft_version, 0)
        self.assertEqual(unchanged.rounds_elapsed, 0)

        companion_mp = self.companion.traits.mp.current
        player_mp = self.player.traits.mp.current
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player,
                _T_ANY_SINGLE,
                [self.monster],
                commanded_actor=self.companion,
            )
        self.assertEqual(result["outcome"], "round")
        self.assertLess(self.companion.traits.mp.current, companion_mp)
        self.assertEqual(self.player.traits.mp.current, player_mp)
        self.assertIsNotNone(read_session(self.player))

        knocked = from_storage(
            {
                **to_storage(read_session(self.player)),
                "knocked_out_ids": [int(self.companion.pk)],
            }
        )
        _persist(self.player, knocked)
        knocked_field = reconstruct_battlefield(self.player, knocked)
        self.assertFalse(knocked_field.is_eligible(str(self.companion.key)))
        self.assertNotIn(
            int(self.companion.pk),
            get_required_combat_actors(knocked, knocked_field),
        )

    @covers_requirement(
        "party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die"
    )
    @covers_requirement(
        "battlefield-action-context::is-present-checks-canonical-battlefield-roster-membership"
    )
    @covers_requirement(
        "battlefield-action-context::sleep-prohibits-actions-while-retaining-ordinary-target-legality"
    )
    def test_sleeping_companion_remains_targetable_and_takes_real_damage(self):
        from world.rules.action import ActionRequest
        from world.rules.combat import run_round
        from world.rules.combat_session import (
            _context_for,
            get_required_combat_actors,
            reconstruct_battlefield,
        )
        from world.rules.combat_session.policies import _party_round_provider
        from world.rules.fatigue import SleepPosture, write_fatigue_state

        write_fatigue_state(self.companion, 0, SleepPosture.FORCED)
        self.companion.traits.hp.base = 50
        self.companion.traits.hp.current = 50
        self.monster.traits.atk_phys.base = 20
        self.monster.traits.agility.base = 100
        engage(self.player, self.monster)
        record = read_session(self.player)
        field = reconstruct_battlefield(self.player, record)
        self.assertTrue(field.is_eligible(str(self.companion.key)))
        self.assertNotIn(
            int(self.companion.pk),
            get_required_combat_actors(record, field),
        )

        context = _context_for(field, record)
        provider = _party_round_provider(
            {
                int(self.player.pk): ActionRequest(
                    self.player, _T_ANY_SINGLE, [self.monster], context
                )
            },
            field,
            record,
        )
        hp_before = self.companion.traits.hp.current
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(field, provider, decision_scope_base=engagement_base())
        targets = [
            entry.target
            for log in logs
            for entry in log.entries
            if entry.kind == "damage"
        ]
        self.assertIn(str(self.companion.key), targets)
        self.assertLess(self.companion.traits.hp.current, hp_before)
        self.assertNotIn(int(self.companion.pk), record.knocked_out_ids)
        self.assertGreater(self.companion.traits.hp.current, 0)

        # A sleeper also genuinely knocked out keeps the knockout state and
        # exclusion: sleep creates no immunity or priority of its own.
        from world.rules.combat_session import (
            _persist,
            from_storage,
            to_storage,
        )
        from world.rules.combat_view import build_combat_view

        knocked = from_storage(
            {
                **to_storage(read_session(self.player)),
                "knocked_out_ids": [int(self.companion.pk)],
            }
        )
        _persist(self.player, knocked)
        states = {
            row.identity: row.state
            for row in build_combat_view(self.player).participants
        }
        self.assertEqual(states[int(self.companion.pk)], "knocked_out")
        knocked_field = reconstruct_battlefield(self.player, knocked)
        self.assertFalse(knocked_field.is_eligible(str(self.companion.key)))
