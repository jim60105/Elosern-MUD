"""Command tests for the player-facing ``設定背景`` background command."""

import unittest

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.background import CmdBackground
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import (
    MAX_PERSONA_FIELD_LENGTH,
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.character_creation import resolve_starting_profile


def _balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result: dict[str, int] = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    return result


class BackgroundCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.at_post_create_character(self.char1)
        activate_player_character(
            self.account,
            self.char1,
            CharacterCreationRequest(
                mode="custom",
                display_name="背景角色",
                age=20,
                apparent_age=20,
                race="human",
                subrace="human_commoner",
                allocations=_balanced_allocations("human", "human_commoner"),
            ),
        )

    def _call(self, args=""):
        return self.call(CmdBackground(), args)

    def test_no_arg_shows_current_or_the_empty_note(self):
        output = self._call()
        self.assertIn("你還沒有設定背景。", output)
        self.assertIn("用法：設定背景", output)

    def test_set_persists_the_background(self):
        output = self._call("在公會登記的新人冒險者")
        self.assertIn("已設定背景", output)
        self.assertEqual(
            self.char1.db.persona["background"], "在公會登記的新人冒險者"
        )

    def test_no_arg_shows_the_set_value(self):
        self._call("在公會登記的新人冒險者")
        output = self._call()
        self.assertIn("目前背景：在公會登記的新人冒險者", output)

    def test_clear_removes_the_background(self):
        self._call("背景文字")
        self._call(" ")
        self.assertNotIn("background", self.char1.db.persona)
        output = self._call()
        self.assertIn("你還沒有設定背景。", output)

    def test_over_bound_input_is_rejected(self):
        output = self._call("x" * (MAX_PERSONA_FIELD_LENGTH + 1))
        self.assertIn("超過", output)
        self.assertIsNone(self.char1.db.persona)

    def test_update_changes_only_the_background_field(self):
        self.char1.db.persona = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "故事",
            "habit": "習慣",
            "appearance": {},
            "social_connection": {},
        }
        self._call("新背景")
        stored = self.char1.db.persona
        self.assertEqual(stored["background"], "新背景")
        self.assertEqual(stored["personality"], "沉穩")
        # Balanced allocation spends the budget on hp/mp/sp first; the
        # magic_power axis gets 0, so the trait sits at the human floor (5).
        self.assertEqual(self.char1.traits.magic_power.value, 5)

    def test_works_without_a_persona_record(self):
        self.char1.attributes.remove("persona")
        self._call("無卡片也能設定")
        self.assertEqual(
            self.char1.db.persona["background"], "無卡片也能設定"
        )

    def test_alias_背景_reaches_the_same_command(self):
        output = self.call(CmdBackground(), "用別名設定")
        self.assertIn("已設定背景", output)
        self.assertEqual(self.char1.db.persona["background"], "用別名設定")


if __name__ == "__main__":
    unittest.main()
