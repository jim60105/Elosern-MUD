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
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    bank_fixed,
    banked_epithets,
    bank_epithet,
    decline_records,
    grant_starter_pair,
    persist_nomination_ballot,
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


_NO_BALLOT = "目前沒有待決的異名提名。"
_BAD_INDEX = "沒有這個編號的提名。"


class TitleBallotCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """``title accept`` / ``title decline`` against a real pending ballot."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="ballot command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def _ballot(self):
        self.assertTrue(
            persist_nomination_ballot(
                self.actor,
                [
                    {"display": "火焰之心", "basis": "焚盡匪寨"},
                    {"display": "破曉之刃", "basis": "曙間退敵"},
                ],
            )
        )

    def test_usage_lists_the_ballot_verbs(self):
        output = self._call("")
        self.assertIn("title accept <1|2|3>", output)
        self.assertIn("title decline", output)

    def test_answers_without_ballot_use_the_stable_line(self):
        for args in ("accept", "accept 1", "decline"):
            with self.subTest(args=args):
                self.assertEqual(self._call(args), _NO_BALLOT)
        self.assertFalse(self.actor.attributes.has(PENDING_BALLOT_KEY))

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_bare_accept_lists_the_ballot(self):
        self._ballot()
        output = self._call("accept")
        self.assertIn("◆ 異名提名（待決）", output)
        self.assertIn("1. 火焰之心——焚盡匪寨", output)
        self.assertIn("2. 破曉之刃——曙間退敵", output)
        self.assertEqual(len(read_title_state(self.actor)[0]), 0)

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_accept_records_the_numbered_choice(self):
        self._ballot()
        self.assertEqual(self._call("accept 1"), "你採納異名：火焰之心")
        collection, equipped = read_title_state(self.actor)
        self.assertEqual([e["display"] for e in collection], ["火焰之心"])
        self.assertEqual(equipped["epithet"], "火焰之心")
        self.assertFalse(self.actor.attributes.has(PENDING_BALLOT_KEY))
        # A second answer has nothing to answer.
        self.assertEqual(self._call("accept 1"), _NO_BALLOT)
        self.assertEqual(self._call("decline"), _NO_BALLOT)

    def test_accept_rejects_out_of_range_and_non_numeric(self):
        self._ballot()
        for args in ("accept 3", "accept 0", "accept abc", "accept -1"):
            with self.subTest(args=args):
                self.assertEqual(self._call(args), _BAD_INDEX)
        self.assertTrue(self.actor.attributes.has(PENDING_BALLOT_KEY))

    def test_accept_reports_already_owned_epithet(self):
        grant_starter_pair(self.actor)
        self.assertTrue(
            persist_nomination_ballot(
                self.actor, [{"display": "南門新客", "basis": "再度入票"}]
            )
        )
        self.assertEqual(self._call("accept 1"), "你早已擁有異名：南門新客")
        self.assertFalse(self.actor.attributes.has(PENDING_BALLOT_KEY))
        self.assertEqual(len(read_title_state(self.actor)[0]), 2)

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_decline_consumes_ballot_and_starts_the_record(self):
        self._ballot()
        output = self._call("decline")
        self.assertIn("拒絕了異名提名", output)
        self.assertIn("火焰之心", output)
        self.assertIn("破曉之刃", output)
        self.assertFalse(self.actor.attributes.has(PENDING_BALLOT_KEY))
        records = decline_records(self.actor)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["displays"], ("火焰之心", "破曉之刃"))

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_list_shows_the_pending_ballot_section(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        self._ballot()
        output = self._call("list")
        self.assertIn("◆ 異名提名（待決）", output)
        self.assertIn("title accept <編號>", output)
        # After accepting, the section is gone.
        self._call("accept 2")
        self.assertNotIn("◆ 異名提名（待決）", self._call("list"))

    def test_malformed_ballot_presents_stable_lines_and_writes_nothing(self):
        self.actor.attributes.add(PENDING_BALLOT_KEY, [{"display": "缺 basis"}])
        # Strict readers fail closed: the answer surfaces present the fixed
        # unavailable line and the bare listing degrades to "nothing pending".
        self.assertEqual(self._call("accept 1"), _UNAVAILABLE)
        self.assertEqual(self._call("decline"), _UNAVAILABLE)
        self.assertEqual(self._call("accept"), _NO_BALLOT)
        self.assertNotIn("◆ 異名提名", self._call("list"))
        # The malformed face stays untouched (the writer fails closed too).
        self.assertEqual(
            self.actor.attributes.get(PENDING_BALLOT_KEY, default=None),
            [{"display": "缺 basis"}],
        )


_REMOVE_UNKNOWN = "無法移除該異名。"
_REMOVE_LAST = "至少需保留一個異名。"
_REMOVE_EQUIPPED = "裝備中的異名無法移除，請先改掛其他異名。"


class TitleCodexCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """``title codex`` text rendering from the same pure view as the panel."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="codex command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def test_codex_renders_header_counters_marks_and_basis_lines(self):
        grant_starter_pair(self.actor)
        bank_epithet(self.actor, "破城先鋒", "率先破門。", 500)
        output = self._call("codex")
        self.assertIn("── 稱號冊 ──", output)
        self.assertIn("當前全銜：F級冒險者　南門新客", output)
        self.assertIn("已解鎖 1 /", output)
        # Fixed block: unlocked banked mark without hint, locked row with hint.
        self.assertIn("　● F級冒險者", output)
        self.assertIn(
            f"　○ S級傳說（{FIXED_TITLE_REGISTRY['g_s_rank'].hint_zh}）", output
        )
        # Epithet block: equipped row stars WITHOUT the removable suffix; the
        # unequipped second row carries （可移除） and its basis quote line.
        self.assertIn("　★ 南門新客", output)
        self.assertNotIn("南門新客（可移除）", output)
        self.assertIn("　● 破城先鋒（可移除）", output)
        self.assertIn("　　─ 率先破門。", output)

    def test_codex_renders_the_ballot_section_when_pending(self):
        grant_starter_pair(self.actor)
        self.assertTrue(
            persist_nomination_ballot(
                self.actor, [{"display": "夜襲之人", "basis": "夜半三度出入敵陣。"}]
            )
        )
        output = self._call("codex")
        self.assertIn("◆ 異名提名（待決）", output)
        self.assertIn("夜襲之人", output)
        self.assertIn("title accept", output)

    def test_codex_reports_an_empty_epithet_block_and_malformed_line(self):
        bank_fixed(self.actor, "g_f_rank", 1)
        self.assertIn("（尚未取得）", self._call("codex"))
        self.actor.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        self.assertEqual(self._call("codex"), _UNAVAILABLE)


class TitleRemovalCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """The two-step ``title remove epithet`` flow at the command surface."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="removal command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def _bank_pair(self):
        grant_starter_pair(self.actor)
        bank_epithet(self.actor, "破城先鋒", "率先破門。", 500)

    def test_gated_targets_answer_stable_lines_and_never_enter_review(self):
        self._bank_pair()
        before = read_title_state(self.actor)
        for args, line in (
            ("remove epithet 不存在", _REMOVE_UNKNOWN),
            ("remove epithet g_f_rank", _REMOVE_UNKNOWN),
            ("remove epithet 南門新客", _REMOVE_EQUIPPED),
            ("remove epithet 南門新客 confirm", _REMOVE_EQUIPPED),
            ("remove epithet confirm", _REMOVE_UNKNOWN),
        ):
                self.assertEqual(self._call(args), line)
                self.assertEqual(read_title_state(self.actor), before)
        # Sole epithet answers LAST, not EQUIPPED.
        sole = create_object(PlayerCharacter, key="removal sole actor")
        grant_starter_pair(sole)
        self.assertEqual(
            self.call(
                CmdTitle(), "remove epithet 南門新客", caller=sole, receiver=sole
            ),
            _REMOVE_LAST,
        )

    def test_ask_echoes_the_review_card_and_writes_nothing(self):
        self._bank_pair()
        before = (
            read_title_state(self.actor),
            self.actor.attributes.get("title_epithet_removals", default=None),
        )
        output = self._call("remove epithet 破城先鋒")
        self.assertIn("── 異名移除確認 ──", output)
        self.assertIn("　● 破城先鋒", output)
        self.assertIn("　　─ 率先破門。", output)
        self.assertIn("此操作不可恢復。", output)
        self.assertIn(
            "確認請輸入：title remove epithet 破城先鋒 confirm", output
        )
        self.assertIn("輸入其他任何內容即取消", output)
        # Stateless: the echo stores NOTHING; the next unrelated command is
        # an ordinary command, and the state is byte-identical.
        self.assertEqual(read_title_state(self.actor), before[0])
        self.assertEqual(self.actor.attributes.get("title_epithet_removals", default=None), before[1])
        self.assertEqual(self._call("list"), self._call("list"))

    def test_confirm_executes_and_renders_the_removal_line(self):
        self._bank_pair()
        output = self._call("remove epithet 破城先鋒 confirm")
        self.assertIn("放下了異名：破城先鋒", output)
        _collection, equipped = read_title_state(self.actor)
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            ["南門新客"],
        )
        self.assertEqual(
            equipped, {"fixed": "g_f_rank", "epithet": "南門新客"}
        )
        records = self.actor.attributes.get("title_epithet_removals")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["display"], "破城先鋒")
        # The codex re-render drops the row entirely.
        self.assertNotIn("破城先鋒", self._call("codex"))

    def test_quoted_confirm_tail_round_trips(self):
        # A display whose tail would eat the confirm token is echoed quoted
        # and parses back through one matching quote pair.
        grant_starter_pair(self.actor)
        bank_epithet(self.actor, "破門 confirm", "尾綴陷阱。", 500)
        output = self._call("remove epithet 破門 confirm")
        # Unquoted, the trailing token IS stripped and "破門" alone is an
        # unknown target — the stable unknown line, not a review card.
        self.assertEqual(output, _REMOVE_UNKNOWN)
        self.assertEqual(
            self._call('remove epithet "破門 confirm"'),
            self._call('remove epithet "破門 confirm"'),
        )
        review = self._call('remove epithet "破門 confirm"')
        self.assertIn("── 異名移除確認 ──", review)
        self.assertIn(
            '確認請輸入：title remove epithet "破門 confirm" confirm', review
        )
        done = self._call('remove epithet "破門 confirm" confirm')
        self.assertIn("放下了異名：破門 confirm", done)
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            ["南門新客"],
        )

    def test_bare_confirm_token_is_a_target_not_a_confirmation(self):
        # `title remove epithet confirm` does NOT confirm anything: the
        # single trailing token only counts as confirmation when a display
        # precedes it, so bare `confirm` reads as an unknown target and an
        # empty quoted display falls to usage. No blind execution path.
        self._bank_pair()
        self.assertEqual(self._call("remove epithet confirm"), _REMOVE_UNKNOWN)
        self.assertIn("語法：title list", self._call('remove epithet "" confirm'))
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            ["南門新客", "破城先鋒"],
        )

    @covers_requirement(
        "title-system::epithet-removal-is-the-only-delete-path-and-gates-precede-confirmation"
    )
    def test_remove_fixed_has_no_delete_surface_at_all(self):
        self._bank_pair()
        before = read_title_state(self.actor)
        for args in ("remove fixed g_f_rank", "remove fixed 破城先鋒", "remove"):
            with self.subTest(args=args):
                self.assertIn("語法：title list", self._call(args))
        self.assertEqual(read_title_state(self.actor), before)

    @covers_requirement(
        "title-system::codex-surfaces-remain-consistent-across-sessions"
    )
    def test_removed_state_survives_an_attribute_cache_reset(self):
        # Logout/reload analog: a cache reset forces a durable re-read.
        self._bank_pair()
        self._call("remove epithet 破城先鋒 confirm")
        self.actor.attributes.reset_cache()
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            ["南門新客"],
        )
        records = self.actor.attributes.get("title_epithet_removals")
        self.assertEqual(records[0]["display"], "破城先鋒")
        self.assertNotIn("破城先鋒", self._call("codex"))
