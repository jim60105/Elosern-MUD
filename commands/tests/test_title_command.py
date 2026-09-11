"""Player-facing ``title`` command tests: listing, swap-only equip, no oracle.

Drives ``title list``, ``title equip fixed``, and ``title equip epithet``
through the command layer: the full-title header, banked versus locked rows with
their authored hints, both accepted identifier forms, the single stable
rejection line that never enumerates candidates, the fixed unavailable line for
malformed state, and the usage line for anything else. It also pins the mount
(key ``title``, no aliases) and that the equip surface can never empty a slot.

The fixed-title ledger is the kit + locally authored rows (test-data-independence):
displays, hints, and epithets are invented; the bank/lock rendering is read
from the scoped registry at runtime.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.default_cmdsets import CharacterCmdSet
from commands.title import CmdTitle
from typeclasses.characters import PlayerCharacter
from world.rules.titles import (
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    bank_fixed,
    banked_epithets,
    bank_epithet,
    decline_records,
    persist_nomination_ballot,
    read_title_state,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import make_title

_REJECTED = "無法掛上該稱號。"
_UNAVAILABLE = "你的稱號冊暫時無法閱讀。"

# Locally authored fixed-title ledger (three rows: bank one, keep one locked,
# order rows against registry insertion).
_T_BRONZE = make_title(
    "t_bronze", display_name_zh="銅級見習", hint_zh="在合成公會登記即可獲得。"
)
_T_SILVER = make_title(
    "t_silver", display_name_zh="銀級委託人", hint_zh="通過銀級考核即可獲得。"
)
_T_GOLD = make_title("t_gold", display_name_zh="金級巨匠", hint_zh="金級考核的終極榮耀。")
_TITLES = {row.key: row for row in (_T_BRONZE, _T_SILVER, _T_GOLD)}
_TITLES_EXTRA = {"titles": _TITLES}

# Invented epithet vocabulary.
_STARTER_EPITHET = "霧原新人"
_STARTER_BASIS = "首次領取委託的記號。"
_SECOND_EPITHET = "垣根拓先鋒"
_SECOND_BASIS = "率先破門。"

# Bank ticks are arbitrary integers; the command surface never reads the clock.
_TICK = 1


def _grant_starter(actor):
    """Bank+auto-equip the invented starter epithet (mirror of the shipped grant)."""
    assert bank_epithet(actor, _STARTER_EPITHET, _STARTER_BASIS, _TICK)


class _TitleScopeMixin:
    """Run against the locally authored fixed-title ledger."""

    def setUp(self):
        open_synthetic_scope(self, "titles", extra=_TITLES_EXTRA)
        super().setUp()


class TitleCommandTests(_TitleScopeMixin, EvenniaCommandTestMixin, EvenniaTest):
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
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        output = self._call("list")
        self.assertIn("── 稱號冊 ──", output)
        self.assertIn(
            f"當前全銜：{_T_BRONZE.display_name_zh}　{_STARTER_EPITHET}", output
        )
        for entry in _TITLES.values():
            self.assertIn(entry.display_name_zh, output)
        # A banked row carries no hint; a locked row carries its authored hint.
        self.assertIn(f"● {_T_BRONZE.display_name_zh}", output)
        self.assertNotIn(f"{_T_BRONZE.display_name_zh}（", output)
        self.assertIn(
            f"○ {_T_GOLD.display_name_zh}（{_T_GOLD.hint_zh}）", output
        )
        self.assertIn(f"● {_STARTER_EPITHET}", output)

    def test_list_reports_an_empty_epithet_block(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        output = self._call("list")
        self.assertIn("◆ 異名", output)
        self.assertIn("（尚未取得）", output)

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_fixed_accepts_key_or_display_and_reports_the_new_title(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        bank_fixed(self.actor, _T_SILVER.key, _TICK + 1)
        self.assertEqual(
            self._call("equip fixed t_silver"), f"你掛上稱號：{_T_SILVER.display_name_zh}"
        )
        self.assertEqual(read_title_state(self.actor)[1]["fixed"], _T_SILVER.key)
        self.assertEqual(
            self._call(f"equip fixed {_T_BRONZE.display_name_zh}"),
            f"你掛上稱號：{_T_BRONZE.display_name_zh}",
        )
        self.assertEqual(read_title_state(self.actor)[1]["fixed"], _T_BRONZE.key)
        # Re-equipping the current row is inert and still reports the title.
        self.assertEqual(
            self._call(f"equip fixed {_T_BRONZE.key}"),
            f"你掛上稱號：{_T_BRONZE.display_name_zh}",
        )
        self.assertEqual(read_title_state(self.actor)[0][1]["key"], _T_SILVER.key)

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_equip_epithet_swaps_between_banked_epithets(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        bank_epithet(self.actor, "霧門新客", "守衛的目送", _TICK)
        bank_epithet(self.actor, "夜影行者", "夜裡的眼", _TICK + 1)
        self.assertEqual(self._call("equip epithet 夜影行者"), "你掛上異名：夜影行者")
        self.assertEqual(read_title_state(self.actor)[1]["epithet"], "夜影行者")
        self.assertEqual(self._call("equip epithet 霧門新客"), "你掛上異名：霧門新客")
        # A multi-word display parses as one display name.
        bank_epithet(self.actor, "霧門 新客 二", "第二段引文", _TICK + 2)
        self.assertEqual(
            self._call("equip epithet 霧門 新客 二"), "你掛上異名：霧門 新客 二"
        )

    @covers_requirement("title-system::the-title-equip-surface-swaps-identifiers-and-never-un-equips")
    def test_every_rejection_shares_one_line_without_candidate_leakage(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        bank_epithet(self.actor, "霧門新客", "守衛的目送", _TICK)
        cases = (
            f"equip fixed {_T_GOLD.display_name_zh}",
            "equip fixed 不存在的稱號",
            "equip fixed 霧門新客",
            f"equip epithet {_T_BRONZE.display_name_zh}",
            "equip epithet 未取得的異名",
            "equip epithet t_bronze",
            "equip fixed t_gold",
        )
        for args in cases:
            with self.subTest(args=args):
                output = self._call(args)
                self.assertEqual(output, _REJECTED)
                for hidden in (_T_SILVER.display_name_zh, "銀級傭兵", _T_SILVER.key, "夜影行者"):
                    self.assertNotIn(hidden, output)
                # A rejected equip leaves both slots exactly as they were.
                self.assertEqual(
                    read_title_state(self.actor)[1],
                    {"fixed": _T_BRONZE.key, "epithet": "霧門新客"},
                )

    def test_malformed_state_presents_the_unavailable_line_and_writes_nothing(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        self.actor.attributes.add(TITLE_COLLECTION_KEY, "damaged")
        for args in ("list", "equip fixed t_silver", "equip epithet 霧門新客"):
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


class TitleBallotCommandTests(_TitleScopeMixin, EvenniaCommandTestMixin, EvenniaTest):
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
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        self.assertTrue(
            persist_nomination_ballot(
                self.actor, [{"display": _STARTER_EPITHET, "basis": "再度入票"}]
            )
        )
        self.assertEqual(self._call("accept 1"), f"你早已擁有異名：{_STARTER_EPITHET}")
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
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
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


class TitleCodexCommandTests(_TitleScopeMixin, EvenniaCommandTestMixin, EvenniaTest):
    """``title codex`` text rendering from the same pure view as the panel."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="codex command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def test_codex_renders_header_counters_marks_and_basis_lines(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        bank_epithet(self.actor, _SECOND_EPITHET, _SECOND_BASIS, _TICK + 1)
        output = self._call("codex")
        self.assertIn("── 稱號冊 ──", output)
        self.assertIn(
            f"當前全銜：{_T_BRONZE.display_name_zh}　{_STARTER_EPITHET}", output
        )
        self.assertIn("已解鎖 1 /", output)
        # Fixed block: unlocked banked mark without hint, locked row with hint.
        self.assertIn(f"　● {_T_BRONZE.display_name_zh}", output)
        self.assertIn(
            f"　○ {_T_GOLD.display_name_zh}（{_T_GOLD.hint_zh}）", output
        )
        # Epithet block: equipped row stars WITHOUT the removable suffix; the
        # unequipped second row carries （可移除） and its basis quote line.
        self.assertIn(f"　★ {_STARTER_EPITHET}", output)
        self.assertNotIn(f"{_STARTER_EPITHET}（可移除）", output)
        self.assertIn(f"　● {_SECOND_EPITHET}（可移除）", output)
        self.assertIn(f"　　─ {_SECOND_BASIS}", output)

    def test_codex_renders_the_ballot_section_when_pending(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
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
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        self.assertIn("（尚未取得）", self._call("codex"))
        self.actor.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        self.assertEqual(self._call("codex"), _UNAVAILABLE)


class TitleRemovalCommandTests(_TitleScopeMixin, EvenniaCommandTestMixin, EvenniaTest):
    """The two-step ``title remove epithet`` flow at the command surface."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="removal command actor")

    def _call(self, args):
        return self.call(CmdTitle(), args, caller=self.actor, receiver=self.actor)

    def _bank_pair(self):
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        bank_epithet(self.actor, _SECOND_EPITHET, _SECOND_BASIS, _TICK + 1)

    def test_gated_targets_answer_stable_lines_and_never_enter_review(self):
        self._bank_pair()
        before = read_title_state(self.actor)
        for args, line in (
            ("remove epithet 不存在", _REMOVE_UNKNOWN),
            ("remove epithet t_bronze", _REMOVE_UNKNOWN),
            (f"remove epithet {_STARTER_EPITHET}", _REMOVE_EQUIPPED),
            (f"remove epithet {_STARTER_EPITHET} confirm", _REMOVE_EQUIPPED),
            ("remove epithet confirm", _REMOVE_UNKNOWN),
        ):
                self.assertEqual(self._call(args), line)
                self.assertEqual(read_title_state(self.actor), before)
        # Sole epithet answers LAST, not EQUIPPED.
        sole = create_object(PlayerCharacter, key="removal sole actor")
        _grant_starter(sole)
        self.assertEqual(
            self.call(
                CmdTitle(),
                f"remove epithet {_STARTER_EPITHET}",
                caller=sole,
                receiver=sole,
            ),
            _REMOVE_LAST,
        )

    def test_ask_echoes_the_review_card_and_writes_nothing(self):
        self._bank_pair()
        before = (
            read_title_state(self.actor),
            self.actor.attributes.get("title_epithet_removals", default=None),
        )
        output = self._call(f"remove epithet {_SECOND_EPITHET}")
        self.assertIn("── 異名移除確認 ──", output)
        self.assertIn(f"　● {_SECOND_EPITHET}", output)
        self.assertIn(f"　　─ {_SECOND_BASIS}", output)
        self.assertIn("此操作不可恢復。", output)
        self.assertIn(
            f"確認請輸入：title remove epithet {_SECOND_EPITHET} confirm", output
        )
        self.assertIn("輸入其他任何內容即取消", output)
        # Stateless: the echo stores NOTHING; the next unrelated command is
        # an ordinary command, and the state is byte-identical.
        self.assertEqual(read_title_state(self.actor), before[0])
        self.assertEqual(self.actor.attributes.get("title_epithet_removals", default=None), before[1])
        self.assertEqual(self._call("list"), self._call("list"))

    def test_confirm_executes_and_renders_the_removal_line(self):
        self._bank_pair()
        output = self._call(f"remove epithet {_SECOND_EPITHET} confirm")
        self.assertIn(f"放下了異名：{_SECOND_EPITHET}", output)
        _collection, equipped = read_title_state(self.actor)
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            [_STARTER_EPITHET],
        )
        self.assertEqual(
            equipped, {"fixed": _T_BRONZE.key, "epithet": _STARTER_EPITHET}
        )
        records = self.actor.attributes.get("title_epithet_removals")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["display"], _SECOND_EPITHET)
        # The codex re-render drops the row entirely.
        self.assertNotIn(_SECOND_EPITHET, self._call("codex"))

    def test_quoted_confirm_tail_round_trips(self):
        # A display whose tail would eat the confirm token is echoed quoted
        # and parses back through one matching quote pair.
        bank_fixed(self.actor, _T_BRONZE.key, _TICK)
        _grant_starter(self.actor)
        bank_epithet(self.actor, "破門 confirm", "尾綴陷阱。", _TICK + 1)
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
            [_STARTER_EPITHET],
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
            [_STARTER_EPITHET, _SECOND_EPITHET],
        )

    @covers_requirement(
        "title-system::epithet-removal-is-the-only-delete-path-and-gates-precede-confirmation"
    )
    def test_remove_fixed_has_no_delete_surface_at_all(self):
        self._bank_pair()
        before = read_title_state(self.actor)
        for args in (
            f"remove fixed {_T_BRONZE.key}",
            f"remove fixed {_SECOND_EPITHET}",
            "remove",
        ):
            with self.subTest(args=args):
                self.assertIn("語法：title list", self._call(args))
        self.assertEqual(read_title_state(self.actor), before)

    @covers_requirement(
        "title-system::codex-surfaces-remain-consistent-across-sessions"
    )
    def test_removed_state_survives_an_attribute_cache_reset(self):
        # Logout/reload analog: a cache reset forces a durable re-read.
        self._bank_pair()
        self._call(f"remove epithet {_SECOND_EPITHET} confirm")
        self.actor.attributes.reset_cache()
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.actor)],
            [_STARTER_EPITHET],
        )
        records = self.actor.attributes.get("title_epithet_removals")
        self.assertEqual(records[0]["display"], _SECOND_EPITHET)
        self.assertNotIn(_SECOND_EPITHET, self._call("codex"))
