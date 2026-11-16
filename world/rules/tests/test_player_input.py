"""Behaviour tests: the process-wide record of the last player input."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from world.rules import player_input


class PlayerInputTests(unittest.TestCase):
    """The record answers ``None`` until an input is noted, then its age."""

    def setUp(self) -> None:
        player_input.reset_player_input()

    def tearDown(self) -> None:
        player_input.reset_player_input()

    def test_no_input_recorded_answers_none(self) -> None:
        self.assertIsNone(player_input.seconds_since_player_input())

    def test_age_is_the_time_since_the_noted_input(self) -> None:
        with patch("world.rules.player_input._now", return_value=100.0):
            player_input.note_player_input()

        with patch("world.rules.player_input._now", return_value=102.5):
            self.assertEqual(player_input.seconds_since_player_input(), 2.5)

    def test_reset_forgets_the_noted_input(self) -> None:
        with patch("world.rules.player_input._now", return_value=100.0):
            player_input.note_player_input()

        player_input.reset_player_input()

        self.assertIsNone(player_input.seconds_since_player_input())


if __name__ == "__main__":
    unittest.main()
