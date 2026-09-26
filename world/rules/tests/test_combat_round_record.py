"""Round-record integration tests for the combat beats (design D1).

The round transaction records the roster identities and every participant's
stored HP before the round and at its committed end, attaches them to the
result as an internal ``round_record``, and records only the round's own event
logs. These tests drive the real facade against the synthetic kit.
"""

from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.action import stored_gauge_pair
from world.rules.combat_beats import RoundRecord
from world.rules.combat_session import (
    engage,
    forfeit,
    read_session,
    submit_player_action,
)
from world.rules.combat_view import build_combat_view
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.tests.synthetic_data import SYNTH_SKILLS


# File-local cast row: a synthetic single-target elemental spell built from the
# kit template under a t_-key, mirroring the dispatcher integration fixture.
_T_CAST = replace(
    SYNTH_SKILLS["t_ember_burst"],
    key="t_record_bolt",
    label="紀錄試術",
    description="回合紀錄整合測試專用的合成單體法術。",
)


@contextmanager
def _hit_rolls():
    """Patch every roll site so one round resolves deterministically with hits."""
    with (
        patch("world.rules.combat.battlefield.roll_d100", return_value=100),
        patch("world.rules.combat.damage.roll_d100", return_value=100),
        patch("world.rules.combat.rounds.roll_d100", return_value=100),
    ):
        yield


class CombatRoundRecordTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    **synth_innate_overlay()["skills"],
                    _T_CAST.key: _T_CAST,
                }
            },
        )
        super().setUp()
        self.room = create_object(Room, key="record arena")
        self.player = create_object(PlayerCharacter, key="record player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST.key])
        self.monster = create_object(Monster, key="record goblin")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        self.monster.traits.hp.base = 100
        self.monster.traits.hp.current = 100
        self.monster.location = self.room

    def _hp(self, entity) -> int:
        return stored_gauge_pair(entity, "hp")[0]

    def test_a_non_terminal_round_records_the_committed_hp(self):
        engage(self.player, self.monster)
        hp_before = {
            int(self.player.pk): self._hp(self.player),
            int(self.monster.pk): self._hp(self.monster),
        }
        with _hit_rolls():
            result = submit_player_action(self.player, _T_CAST.key, [self.monster])
        self.assertEqual(result["outcome"], "round")
        record = result["round_record"]
        self.assertIsInstance(record, RoundRecord)
        session = read_session(self.player)
        self.assertEqual(record.session_id, session.session_id)
        self.assertEqual(record.number, session.rounds_elapsed)
        self.assertEqual(record.round_id, f"{session.session_id}/{session.rounds_elapsed}")
        self.assertEqual(record.hp_before, hp_before)
        self.assertEqual(
            record.identities,
            {str(self.player.key): int(self.player.pk), str(self.monster.key): int(self.monster.pk)},
        )
        # The committed end-of-round HP equals the same revision's combat panel
        # HP for every participant (nothing writes HP between the capture and
        # the presenter).
        view = build_combat_view(self.player)
        self.assertEqual(
            record.hp_after,
            {participant.identity: participant.hp_current for participant in view.participants},
        )
        self.assertTrue(record.logs)
        # Only the round's own logs: a non-terminal result's logs are exactly
        # the round's.
        self.assertEqual(record.logs, tuple(result["logs"]))

    def test_a_terminal_round_records_the_foe_at_zero(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        with _hit_rolls():
            result = submit_player_action(self.player, _T_CAST.key, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        record = result["round_record"]
        self.assertIsInstance(record, RoundRecord)
        self.assertEqual(record.hp_after[int(self.monster.pk)], 0)
        # The defeat aftermath appends its own logs to the terminal result;
        # the record keeps only the round's prefix.
        self.assertLessEqual(len(record.logs), len(result["logs"]))
        self.assertEqual(record.logs, tuple(result["logs"])[: len(record.logs)])

    def test_a_preflight_rejection_carries_no_record(self):
        self.player.traits.mp.base = 0
        self.player.traits.mp.current = 0
        engage(self.player, self.monster)
        result = submit_player_action(self.player, _T_CAST.key, [self.monster])
        self.assertEqual(result["outcome"], "rejected")
        self.assertNotIn("round_record", result)

    def test_forfeit_carries_no_record(self):
        engage(self.player, self.monster)
        result = forfeit(self.player)
        self.assertNotIn("round_record", result)


if __name__ == "__main__":
    unittest.main()
