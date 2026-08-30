"""Player-facing ``title`` command tests: listing, swap-only equip, no oracle.

Drives ``title list``, ``title equip fixed``, and ``title equip epithet``
through the command layer: the full-title header, banked versus locked rows with
their authored hints, both accepted identifier forms, the single stable
rejection line that never enumerates candidates, the fixed unavailable line for
malformed state, and the usage line for anything else. It also pins the mount
(key ``title``, no aliases) and that the equip surface can never empty a slot.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.default_cmdsets import CharacterCmdSet
from commands.title import CmdTitle
from typeclasses.characters import PlayerCharacter
from world.lore.titles import FIXED_TITLE_REGISTRY, STARTER_EPITHET
from world.rules.titles import (
    TITLE_COLLECTION_KEY,
    bank_fixed,
    bank_epithet,
    grant_starter_pair,
    read_title_state,
)

_REJECTED = "無法掛上該稱號。"
_UNAVAILABLE = "你的稱號冊暫時無法閱讀。"


class TitleCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """The whole ``title`` surface against a real player character."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="title command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def test_usage_line_for_an_empty_or_unknown_invocation(self):
        for args in ("", "list extra", "equip", "equip fixed", "bogus", "equip widget x"):
            with self.subTest(args=args):
                self.assertIn("語法：title list", self._call(args))

    def test_list_shows_the_full_title_and_every_registry_row(self):
        grant_starter_pair(self.actor)
        output = self._call("list")
        self.assertIn("── 稱號冊 ──", output)
        self.assertIn(f"當前全銜：F級冒險者　{STARTER_EPITHET.display}", output)
        for entry in FIXED_TITLE_REGISTRY.values():
            self.assertIn(entry.display_name_zh, output)
        # A banked row carries no hint; a locked row carries its authored hint.
        self.assertIn("● F級冒險者", output)
        self.assertNotIn("F級冒險者（", output)
        self.assertIn(
            f"○ S級傳說（{FIXED_TITLE_REGISTRY['g_s_rank'].hint_zh}）", output
        )
        self.assertIn(f"● {STARTER_EPITHET.display}", output)

    def test_list_reports_an_empty_epithet_block(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        output = self._call("list")
        self.assertIn("◆ 異名", output)
        self.assertIn("（尚未取得）", output)

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_fixed_accepts_key_or_display_and_reports_the_new_title(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        bank_fixed(self.actor, "g_e_rank", 2)
        self.assertEqual(self._call("equip fixed g_e_rank"), "你掛上稱號：E級斥候")
        self.assertEqual(read_title_state(self.actor)[1]["fixed"], "g_e_rank")
        self.assertEqual(self._call("equip fixed F級冒險者"), "你掛上稱號：F級冒險者")
        self.assertEqual(read_title_state(self.actor)[1]["fixed"], "g_f_rank")
        # Re-equipping the current row is inert and still reports the title.
        self.assertEqual(self._call("equip fixed g_f_rank"), "你掛上稱號：F級冒險者")
        self.assertEqual(read_title_state(self.actor)[0][1]["key"], "g_e_rank")

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_epithet_swaps_between_banked_epithets(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        bank_epithet(self.actor, "南門新客", "守衛的目送", 1)
        bank_epithet(self.actor, "夜行者", "夜裡的眼", 2)
        self.assertEqual(self._call("equip epithet 夜行者"), "你掛上異名：夜行者")
        self.assertEqual(read_title_state(self.actor)[1]["epithet"], "夜行者")
        self.assertEqual(self._call("equip epithet 南門新客"), "你掛上異名：南門新客")
        # A multi-word display parses as one display name.
        bank_epithet(self.actor, "南門 新客 二", "第二段引文", 3)
        self.assertEqual(
            self._call("equip epithet 南門 新客 二"), "你掛上異名：南門 新客 二"
        )

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_every_rejection_shares_one_line_without_candidate_leakage(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        bank_epithet(self.actor, "南門新客", "守衛的目送", 1)
        cases = (
            "equip fixed S級傳說",
            "equip fixed 不存在的稱號",
            "equip fixed 南門新客",
            "equip epithet F級冒險者",
            "equip epithet 未取得的異名",
            "equip epithet g_f_rank",
            "equip fixed g_s_rank",
        )
        for args in cases:
            with self.subTest(args=args):
                output = self._call(args)
                self.assertEqual(output, _REJECTED)
                for hidden in ("E級斥候", "D級傭兵", "g_e_rank", "夜行者"):
                    self.assertNotIn(hidden, output)
                # A rejected equip leaves both slots exactly as they were.
                self.assertEqual(
                    read_title_state(self.actor)[1],
                    {"fixed": "g_f_rank", "epithet": "南門新客"},
                )

    def test_malformed_state_presents_the_unavailable_line_and_writes_nothing(self):
        grant_starter_pair(self.actor)
        self.actor.attributes.add(TITLE_COLLECTION_KEY, "damaged")
        for args in ("list", "equip fixed g_e_rank", "equip epithet 南門新客"):
            with self.subTest(args=args):
                self.assertEqual(self._call(args), _UNAVAILABLE)
        self.assertEqual(
            self.actor.attributes.get(TITLE_COLLECTION_KEY, default=None), "damaged"
        )

    def test_command_is_mounted_in_the_character_cmdset(self):
        commands = {command.key: command for command in CharacterCmdSet().commands}
        self.assertIn("title", commands)
        self.assertIsInstance(commands["title"], CmdTitle)
        self.assertFalse(set(commands["title"].aliases))
        self.assertNotIn("稱號", commands)
