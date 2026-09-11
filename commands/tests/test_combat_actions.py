"""Command tests for combat actions and token-parsed session casts (tasks 2.4-2.5)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.action import CmdCast
from commands.combat import CmdCombatActions
from world.lore.elements import Element
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    parse_session_targets,
    resolve_target_token,
)
from world.rules.combat_view import build_combat_view
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

# File-local synthetic spells carry invented element groups, so the
# category/sub-heading ordering mechanics render fully synthetic rows. The
# kit's own element row (t_glowmire) ships in the scoped element registry;
# only the second group is added through the scope extra.
_FEN = Element("t_fenlight", "沼光", "Synthetic element.")
# Row objects, not string keys: SkillDef validates a raw string against the
# LIVE registry at construction time, before any scope is open. The scoped
# registry carries the same-key rows, so runtime resolution still lands.
_GLOW = Element("t_glowmire", "光沼", "Synthetic element.")
_TIDE_ARC = make_skill(
    "t_tide_arc",
    label="潮弧",
    description="彎彎的合成水弧。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 10},
    usable_out_of_combat=True,
    element=_GLOW,
    effects=["damage:t_glowmire:magic"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="t_glowmire",
)
_GALE_JAB = make_skill(
    "t_gale_jab",
    label="風刺",
    description="輕快的合成突刺。",
    kind=SkillKind.ACTIVE,
    # AREA spec: the multi-token cast exercises the multi-target path, which
    # a SINGLE-target skill rejects as a target-spec mismatch.
    target_spec=TargetSpec.AREA,
    cost={"mp": 9},
    usable_out_of_combat=True,
    element=_FEN,
    effects=["damage:t_fenlight:magic"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="t_fenlight",
)
# The kit spell borrows the shipped first-element row (a closed vocabulary
# the kit cannot widen); its key and display label arrive as runtime values
# through the kit row, never as source literals.
_SPELL = SYNTH_SKILLS["t_ember_burst"].key
_SPELL_LABEL = SYNTH_SKILLS["t_ember_burst"].label
_BORROWED_ELEMENT_LABEL = SYNTH_SKILLS["t_ember_burst"].element.display_name_zh

_REED_CUT = make_skill("t_reed_cut", label="蘆斷", description="斷蘆的合成一斬。")

_SCOPE_LOGICALS = (
    "races",
    "static_tiers",
    "subraces",
    "skills",
    "elements",
    "buffs",
    "items",
    "prices",
)


def _scope_extra() -> dict:
    extra = synth_innate_overlay()
    extra["skills"].update(
        {
            _TIDE_ARC.key: _TIDE_ARC,
            _GALE_JAB.key: _GALE_JAB,
            _REED_CUT.key: _REED_CUT,
        }
    )
    extra["elements"] = {_FEN.key: _FEN}
    return extra


def _player(key="token player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "t_duskmari"
    player.apply_race_baseline()
    return player


def _monster(key="token goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class TokenParsingTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "races", "static_tiers", "subraces")
        super().setUp()
        self.room = create_object(Room, key="token arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("token goblin")
        self.monster.location = self.room

    def test_single_token_resolves_from_active_record(self):
        engage(self.player, self.monster)
        self.assertIs(
            resolve_target_token(self.player, "e1"),
            self.monster,
        )
        self.assertIs(
            resolve_target_token(self.player, "a1"),
            self.player,
        )

    def test_token_bounds_reject_unknown_index(self):
        engage(self.player, self.monster)
        for token in ("a2", "e2", "x1", "e0", ""):
            with self.subTest(token=token):
                with self.assertRaises(CombatSessionError):
                    resolve_target_token(self.player, token)

    def test_comma_tokens_resolve_to_explicit_list(self):
        second = _monster("token goblin2")
        second.location = self.room
        engage(self.player, self.monster)
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        record = from_storage(
            {**to_storage(read_session(self.player)), "enemy_ids": [self.monster.pk, second.pk]}
        )
        _persist(self.player, record)
        targets = parse_session_targets(self.player, "e1,e2")
        self.assertEqual(
            [target.key for target in targets],
            ["token goblin", "token goblin2"],
        )

    def test_shorthand_is_passed_through_intact(self):
        engage(self.player, self.monster)
        for shorthand in ("all-enemies", "all-allies", "all"):
            self.assertEqual(
                parse_session_targets(self.player, shorthand),
                shorthand,
            )

    def test_mixed_and_duplicate_syntax_rejects(self):
        engage(self.player, self.monster)
        for value in ("e1,e1", "e1,token goblin", "all-enemies,e1", "token goblin,token goblin"):
            with self.subTest(value=value):
                with self.assertRaises(CombatSessionError):
                    parse_session_targets(self.player, value)

    def test_empty_value_is_empty_list(self):
        engage(self.player, self.monster)
        self.assertEqual(parse_session_targets(self.player, ""), [])
        self.assertEqual(parse_session_targets(self.player, "   "), [])

    def test_display_name_search_retained(self):
        engage(self.player, self.monster)
        result = parse_session_targets(
            self.player,
            "token goblin",
            search=lambda name: self.monster if name == "token goblin" else None,
        )
        self.assertEqual(result, [self.monster])


class CombatActionsCommandTests(BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="combat actions room")
        self.char1.location = self.room
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        grant_lineage(self.char1, [_SPELL])
        self.monster = _monster("actions goblin")
        self.monster.location = self.room

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_combat_actions_lists_skills_and_tokens(self):
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = " ".join(messages)
        self.assertIn("可用技能與目標代號：", messages[0])
        self.assertIn(f"{_SPELL}（{_SPELL_LABEL}）", joined)
        self.assertIn("e1＝actions goblin", joined)
        self.assertIn("a1＝", joined)

    @covers_requirement("webclient-combat-menu::telnet-combat-actions-renders-identical-category-and-group-structure")
    def test_combat_actions_renders_category_headings_and_element_sub_headings(self):
        # Owning skills across two element sub-groups plus a no-group
        # martial-arts skill.
        self.char1.db.skills = {
            "active": [_SPELL, _GALE_JAB.key, _REED_CUT.key],
            "passive": [],
        }
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = "\n".join(messages)
        # Category headings in SkillCategory declaration order: elemental
        # magic, then martial arts (innate basic_attack), then movement
        # (innate flee).
        self.assertIn("◆ 元素魔法", joined)
        self.assertIn("◆ 武技", joined)
        self.assertIn("◆ 移動", joined)
        self.assertLess(joined.index("◆ 元素魔法"), joined.index("◆ 武技"))
        self.assertLess(joined.index("◆ 武技"), joined.index("◆ 移動"))
        # Element sub-headings in ELEMENT_REGISTRY order (the borrowed row
        # stays first in the scoped registry; the invented row follows).
        self.assertIn(f"  {_BORROWED_ELEMENT_LABEL}", joined)
        self.assertIn("  沼光", joined)
        self.assertLess(
            joined.index(f"  {_BORROWED_ELEMENT_LABEL}"), joined.index("  沼光")
        )
        # Skills stay under their element sub-heading in owned_keys order.
        self.assertLess(
            joined.index(f"  {_BORROWED_ELEMENT_LABEL}"),
            joined.index(f"{_SPELL}（{_SPELL_LABEL}）"),
        )
        self.assertLess(joined.index("  沼光"), joined.index("t_gale_jab（風刺）"))
        # The no-group martial-arts category renders no sub-heading: the
        # skill lines follow the heading directly.
        martial = joined[joined.index("◆ 武技") + len("◆ 武技"):joined.index("◆ 移動")]
        self.assertNotIn("◆", martial)
        self.assertIn("t_reed_cut（蘆斷）", martial)
        # The innate overlay re-seeds the production-forced basic-attack key
        # with a synthetic row whose label is authored in the helper.
        self.assertIn("basic_attack（合成基本攻擊）", martial)

    @covers_requirement("webclient-combat-menu::telnet-combat-actions-renders-identical-category-and-group-structure")
    def test_combat_actions_no_group_category_renders_no_sub_heading(self):
        self.char1.db.skills = {"active": [_REED_CUT.key], "passive": []}
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = "\n".join(messages)
        martial = joined[joined.index("◆ 武技"):joined.index("◆ 移動")]
        # The martial-arts heading is followed directly by skill lines; no
        # indented sub-heading line sits between them.
        self.assertIn("◆ 武技\n", joined)
        self.assertIn("t_reed_cut（蘆斷）", martial)

    def test_combat_actions_requires_active_session(self):
        self.call(CmdCombatActions(), "", "目前沒有進行中的戰鬥。")

    def _run(self, cmd_cls, args):
        from unittest.mock import Mock

        self.char1.msg = Mock()
        command = cmd_cls()
        command.caller = self.char1
        command.args = args
        command.func()
        return [call.args[0] for call in self.char1.msg.call_args_list]

    def test_combat_actions_tokens_stable_across_round(self):
        engage(self.char1, self.monster)
        view = build_combat_view(self.char1)
        token_before = next(p.token for p in view.participants if p.identity == self.monster.pk)
        from world.rules.clock import WorldClock
        from world.rules.combat_session import submit_player_action

        with patch("world.rules.clock.get_world_clock", return_value=WorldClock()), patch(
            "world.rules.combat.roll_d100", return_value=100
        ):
            submit_player_action(self.char1, _SPELL, [self.monster])
        view_after = build_combat_view(self.char1)
        token_after = next(p.token for p in view_after.participants if p.identity == self.monster.pk)
        self.assertEqual(token_before, token_after)

    def test_cast_accepts_single_token(self):
        engage(self.char1, self.monster)
        from world.rules.combat_session import read_session

        with patch("world.rules.combat.roll_d100", return_value=100):
            messages = self._run(CmdCast, f"{_SPELL}=e1")
        self.assertTrue(
            any("繼續戰鬥。" in message for message in messages),
            messages,
        )
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    def test_cast_accepts_comma_tokens(self):
        second = _monster("actions goblin2")
        second.location = self.room
        engage(self.char1, self.monster)
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        record = from_storage(
            {**to_storage(read_session(self.char1)), "enemy_ids": [self.monster.pk, second.pk]}
        )
        _persist(self.char1, record)
        self.char1.db.skills = {"active": [_GALE_JAB.key], "passive": []}
        with patch("world.rules.combat.roll_d100", return_value=100):
            messages = self._run(CmdCast, f"{_GALE_JAB.key}=e1,e2")
        self.assertTrue(any("繼續戰鬥。" in m for m in messages), messages)
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    def test_cast_rejects_unknown_token_before_initiative(self):
        engage(self.char1, self.monster)
        with patch("world.rules.combat.roll_d100") as roll:
            messages = self._run(CmdCast, f"{_SPELL}=e9")
        roll.assert_not_called()
        self.assertEqual(self.char1.db.active_combat["rounds_elapsed"], 0)
        self.assertTrue(
            any("無法確認當前戰鬥。" in m for m in messages), messages
        )


class CastCommandSettlementSurfaceTests(unittest.TestCase):
    """Source-inspection: the out-of-combat cast boundary is the settlement API.

    The settlement call returns only after the outer transaction commits, so
    the command's success rendering is post-commit by construction; the
    in-combat session path must never touch the settlement or the clock.
    """

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_out_of_combat_cast_delegates_to_the_settlement(self):
        import inspect

        source = inspect.getsource(CmdCast._cast_out_of_combat)
        self.assertIn("settle_out_of_combat_cast", source)
        self.assertNotIn("get_world_clock", source)
        self.assertNotIn("ActionResolver.resolve", source)
        self.assertNotIn("AdvanceSource", source)

    def test_in_combat_session_cast_path_is_unchanged(self):
        import inspect

        source = inspect.getsource(CmdCast._cast_in_session)
        self.assertIn("submit_player_action", source)
        self.assertNotIn("settle_out_of_combat_cast", source)
        self.assertNotIn("get_world_clock", source)
        self.assertNotIn("AdvanceSource", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
