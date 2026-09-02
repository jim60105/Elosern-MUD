"""Command tests for the ``設定個性`` / ``設定生平`` / ``設定習慣`` family.

Each subclass replicates the ``設定背景`` three-part behaviour verbatim (bare
shows the current value and usage, an argument sets the field, a
whitespace-only argument clears it), and every write routes through the
deterministic ``world.rules.persona_edit`` writer. The existing
``commands/tests/test_background.py`` suite is the regression lock for the
shared ``CmdPersonaFieldBase`` extraction.
"""

import unittest

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.persona import (
    CmdPersonaHabit,
    CmdPersonaLifeStory,
    CmdPersonaPersonality,
)
from tools.spec_traceability import covers_requirement
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


class PersonaCommandTests(EvenniaCommandTestMixin, EvenniaTest):
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
                display_name="人格角色",
                age=20,
                apparent_age=20,
                race="human",
                subrace="human_commoner",
                allocations=_balanced_allocations("human", "human_commoner"),
            ),
        )

    _FAMILY = {
        "personality": (CmdPersonaPersonality, "設定個性", "個性"),
        "life_story": (CmdPersonaLifeStory, "設定生平", "生平"),
        "habit": (CmdPersonaHabit, "設定習慣", "習慣"),
    }

    @covers_requirement("persona-editing::the-persona-command-family-mirrors-the-action-on-telnet")
    def test_bare_shows_the_empty_note_then_the_value(self):
        for field, (cmd, key, label) in self._FAMILY.items():
            with self.subTest(field=field):
                output = self.call(cmd(), "", cmdstring=key)
                self.assertIn(f"你還沒有設定{label}。", output)
                self.assertIn(f"用法：{key}", output)
                self.call(cmd(), f"{label}文字", cmdstring=key)
                output = self.call(cmd(), "", cmdstring=key)
                self.assertIn(f"目前{label}：{label}文字", output)

    @covers_requirement("persona-editing::the-persona-command-family-mirrors-the-action-on-telnet")
    def test_set_persists_only_its_field(self):
        for field, (cmd, key, label) in self._FAMILY.items():
            with self.subTest(field=field):
                self.char1.db.persona = {
                    "identity": {},
                    "personality": "沉穩",
                    "life_story": "舊生平",
                    "habit": "舊習慣",
                    "appearance": {},
                    "social_connection": {},
                    "background": "舊背景",
                }
                output = self.call(cmd(), "新值", cmdstring=key)
                self.assertIn(f"已設定{label}：新值", output)
                stored = self.char1.db.persona
                self.assertEqual(stored[field], "新值")
                # Every other key (family fields, background, structural)
                # keeps its previous value: the command writes one field.
                expected = {
                    "identity": {},
                    "personality": "沉穩",
                    "life_story": "舊生平",
                    "habit": "舊習慣",
                    "appearance": {},
                    "social_connection": {},
                    "background": "舊背景",
                }
                expected[field] = "新值"
                self.assertEqual(stored, expected)

    @covers_requirement("persona-editing::the-persona-command-family-mirrors-the-action-on-telnet")
    def test_whitespace_argument_clears_the_field(self):
        for field, (cmd, key, label) in self._FAMILY.items():
            with self.subTest(field=field):
                self.call(cmd(), "待清除", cmdstring=key)
                output = self.call(cmd(), " ", cmdstring=key)
                self.assertIn(f"已清除{label}", output)
                self.assertNotIn(field, self.char1.db.persona)

    @covers_requirement("persona-editing::the-persona-command-family-mirrors-the-action-on-telnet")
    def test_over_bound_input_is_refused(self):
        for field, (cmd, key, label) in self._FAMILY.items():
            with self.subTest(field=field):
                output = self.call(
                    cmd(), "x" * (MAX_PERSONA_FIELD_LENGTH + 1), cmdstring=key
                )
                self.assertIn("超過", output)
                self.assertIn(f"{label}設定超過", output)
                persona = self.char1.db.persona or {}
                self.assertNotIn(field, persona)

    @covers_requirement("persona-editing::the-persona-command-family-mirrors-the-action-on-telnet")
    def test_aliases_reach_the_same_command(self):
        aliases = {
            "personality": ("個性", CmdPersonaPersonality),
            "life_story": ("生平", CmdPersonaLifeStory),
            "habit": ("習慣", CmdPersonaHabit),
        }
        for field, (alias, cmd) in aliases.items():
            with self.subTest(alias=alias):
                self.call(cmd(), "別名值", cmdstring=alias)
                self.assertEqual(self.char1.db.persona[field], "別名值")
        # The second 設定生平 alias.
        self.call(CmdPersonaLifeStory(), "第二別名", cmdstring="背景故事")
        self.assertEqual(self.char1.db.persona["life_story"], "第二別名")

    def test_works_without_a_persona_record(self):
        self.char1.attributes.remove("persona")
        self.call(CmdPersonaHabit(), "無卡片也能設定", cmdstring="設定習慣")
        self.assertEqual(
            self.char1.db.persona["habit"], "無卡片也能設定"
        )


if __name__ == "__main__":
    unittest.main()
