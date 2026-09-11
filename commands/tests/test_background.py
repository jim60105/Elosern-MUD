"""Command tests for the player-facing ``設定背景`` background command.

The activation fixture runs on the synthetic kit: race, subrace, static-tier,
starting-kit, item, price, and element catalogs are patched before any
character work, so the persona-command mechanics never resolve through
shipped content.
"""

import unittest

# Preimport the import-time-validated equipment rulebook BEFORE the synthetic
# catalogs below can be scoped (world.rules.equipment_effects validates the
# shipped item registry once at first import; importing it at module import —
# the established idiom in world/rules/tests — keeps that validation on the
# shipped rulebook instead of the scoped kit rows).
import world.rules.equipment_effects  # noqa: F401

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
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_SUBRACES,
    synthetic_registries,
)

_SCOPE_LOGICALS = (
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "items",
    "prices",
    "elements",
)


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
        # Activation builds traits and a starting kit against the catalogs,
        # so the scope opens before super().setUp() (class decorator would
        # only wrap the test* methods).
        scope = synthetic_registries(*_SCOPE_LOGICALS)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.account.at_post_create_character(self.char1)
        race_key = next(iter(SYNTH_RACES))
        subrace_key = next(iter(SYNTH_SUBRACES))
        activate_player_character(
            self.account,
            self.char1,
            CharacterCreationRequest(
                mode="custom",
                display_name="背景角色",
                age=20,
                apparent_age=20,
                race=race_key,
                subrace=subrace_key,
                allocations=_balanced_allocations(race_key, subrace_key),
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
        # Balanced allocation spends the budget on the leading axes first, so
        # the last axis receives 0 points and rests on its profile floor —
        # read back from the patched profile, never a pinned number.
        profile = resolve_starting_profile(
            next(iter(SYNTH_RACES)), next(iter(SYNTH_SUBRACES))
        )
        last_axis, (floor, _cap) = profile.bounds[-1]
        self.assertEqual(self.char1.traits[last_axis].value, floor)

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
