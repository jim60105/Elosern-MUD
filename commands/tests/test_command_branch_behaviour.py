"""Focused behavior tests for player-facing command branches."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from commands.action import CmdCast
from commands.character_creation import CmdCharacter, _integer
from commands.combat import CmdCombatForfeit, CmdEngage, CmdGuildExam
from commands.economy import CmdBuy, CmdInventory, CmdSell, CmdShopStock
from commands.guild import (
    CmdGuildAbandon,
    CmdGuildAccept,
    CmdGuildLog,
    CmdGuildMerit,
    CmdGuildRegister,
    CmdGuildRequest,
    CmdGuildTurnIn,
)
from commands.skip import CmdRest, CmdSleep, CmdWaitUntil
from world.quests.runtime import QuestNotFound, QuestState
from world.rules.clock import AdvanceSource, DaypartError
from world.rules.combat_session import CombatSessionError, SessionReason
from world.rules.character_creation import CharacterCreationError
from world.rules.economy import TradeError, TradeReason
from world.rules.guild import GuildDataError, RewardClaimError
from world.rules.guild_exams import ExamReason, GuildExamError
from world.rules.guild_offers import BoardAccessError, GuildOfferError
from world.rules.skip_safety import SkipRejectReason


from tools.spec_traceability import covers_requirement


def _command(command_type, args=""):
    command = command_type()
    command.caller = Mock()
    command.args = args
    return command


class GuildCommandBranchTests(TestCase):
    def test_register_reports_rule_error_and_success(self):
        command = _command(CmdGuildRegister)
        command.resolve_staff = Mock(return_value=object())
        with patch("commands.guild.register_adventurer", side_effect=GuildDataError("bad")):
            command.func()
        command.caller.msg.assert_called_with("註冊失敗：bad")

        command.caller.msg.reset_mock()
        with patch("commands.guild.register_adventurer", return_value={"branch_key": "north"}):
            command.func()
        command.caller.msg.assert_called_with("你已註冊為冒險者，階級 F。公會：north")

    def test_accept_validates_key_and_maps_failures(self):
        command = _command(CmdGuildAccept)
        command.resolve_staff = Mock(return_value=object())
        command.func()
        command.caller.msg.assert_called_with("用法：guild accept <definition_key>")

        for error in (BoardAccessError("closed"), GuildOfferError("missing")):
            command.caller.msg.reset_mock()
            command.args = "quest extra"
            with patch("commands.guild.accept_guild_offer", side_effect=error):
                command.func()
            self.assertIn("無法接取任務", command.caller.msg.call_args.args[0])

    def test_log_handles_invalid_empty_and_populated_records(self):
        command = _command(CmdGuildLog)
        with patch("commands.guild.read_records", side_effect=ValueError("broken")):
            command.func()
        command.caller.msg.assert_called_with("任務記錄有誤：broken")

        command.caller.msg.reset_mock()
        with patch("commands.guild.read_records", return_value=[]):
            command.func()
        command.caller.msg.assert_called_with("你的任務記錄是空的。")

        record = SimpleNamespace(quest_id="q-1", state=QuestState.IN_PROGRESS, stage_index=1)
        command.caller.msg.reset_mock()
        with patch("commands.guild.read_records", return_value=[record]):
            command.func()
        self.assertIn("q-1 [in_progress] 階段 2", command.caller.msg.call_args.args[0])

    def test_abandon_validates_id_and_reports_not_found_and_success(self):
        command = _command(CmdGuildAbandon)
        command.resolve_staff = Mock(return_value=object())
        command.func()
        command.caller.msg.assert_called_with("用法：guild abandon <quest_id>")

        command.args = "q-1"
        command.caller.msg.reset_mock()
        with patch("commands.guild.abandon_guild_quest", side_effect=QuestNotFound("q-1")):
            command.func()
        command.caller.msg.assert_called_with("找不到這個任務。")

        command.caller.msg.reset_mock()
        with patch("commands.guild.abandon_guild_quest", return_value=SimpleNamespace(quest_id="q-1")):
            command.func()
        command.caller.msg.assert_called_with("你放棄了任務 q-1。")

    def test_turnin_validates_id_and_formats_failures_and_reward(self):
        command = _command(CmdGuildTurnIn)
        command.resolve_staff = Mock(return_value=object())
        command.func()
        command.caller.msg.assert_called_with("用法：guild turnin <quest_id>")

        command.args = "q-1"
        for error in (RewardClaimError("early"), GuildDataError("bad")):
            command.caller.msg.reset_mock()
            with patch("commands.guild.turn_in_quest", side_effect=error):
                command.func()
            self.assertIn("無法回報任務", command.caller.msg.call_args.args[0])

        result = {"quest_id": "q-1", "copper": 12, "merit": 3, "items": ["meal"]}
        command.caller.msg.reset_mock()
        with patch("commands.guild.turn_in_quest", return_value=result):
            command.func()
        self.assertIn("獲得 12 銅、功績 3", command.caller.msg.call_args.args[0])

    def test_merit_reports_unregistered_top_and_next_rank(self):
        command = _command(CmdGuildMerit)
        command.caller.guild_rank = None
        command.func()
        command.caller.msg.assert_called_with("你尚未註冊為冒險者。")

        command.caller.guild_rank = "S"
        command.caller.msg.reset_mock()
        with patch("commands.guild.read_counter_trait", return_value=99), patch(
            "commands.guild.get_catalog", return_value=SimpleNamespace(merit_thresholds={})
        ):
            command.func()
        command.caller.msg.assert_called_with("你的階級是 S，累計功績 99。")

        command.caller.guild_rank = "F"
        command.caller.msg.reset_mock()
        with patch("commands.guild.read_counter_trait", return_value=4), patch(
            "commands.guild.get_catalog", return_value=SimpleNamespace(merit_thresholds={"E": 10})
        ):
            command.func()
        self.assertIn("4 / 10 (升階 E)", command.caller.msg.call_args.args[0])

    def test_parse_requested_type_defaults_and_rejects_unknown(self):
        from commands.guild import _parse_requested_type

        self.assertEqual(_parse_requested_type(""), "討伐")
        self.assertEqual(_parse_requested_type("採集"), "採集")
        self.assertIsNone(_parse_requested_type("烤肉"))

    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_request_refuses_escort_with_a_clear_message(self):
        from server.ai_director_service import EscortUnavailableError

        command = _command(CmdGuildRequest, "護衛")
        staff = Mock()
        staff.components.get.return_value.branch_key = "guild_branch_altoria"
        command.resolve_staff = Mock(return_value=staff)
        command.caller.ndb = SimpleNamespace(guild_request_pending=None)
        command.caller.guild_rank = "F"
        with patch(
            "commands.guild.parse_guild_registration",
            return_value={"branch_key": "guild_branch_altoria"},
        ), patch(
            "commands.guild.request_generated_quest",
            side_effect=EscortUnavailableError("no binding flow"),
        ):
            command.func()
        command.caller.msg.assert_called_with(
            "護衛委託目前尚未開放，請選擇其他類型的委託。"
        )

    def test_resolve_deferred_reports_escort_refusal_on_the_pending_path(self):
        from twisted.internet.defer import Deferred

        from commands.guild import _GuildRequestPendingError, _resolve_deferred
        from server.ai_director_service import EscortUnavailableError

        caller = Mock()
        caller.ndb.guild_request_pending = None
        pending = Deferred()
        with self.assertRaises(_GuildRequestPendingError):
            _resolve_deferred(pending, caller)
        pending.addErrback(lambda failure: None)
        pending.errback(EscortUnavailableError("no binding flow"))
        caller.msg.assert_called_with("護衛委託目前尚未開放，請選擇其他類型的委託。")

    def test_resolve_deferred_sync_and_pending_paths(self):
        from twisted.internet.defer import Deferred, fail, succeed
        from twisted.python.failure import Failure

        from commands.guild import _GuildRequestPendingError, _resolve_deferred
        from server.ai_director_service import NoSuitableTemplateError

        posted = SimpleNamespace(
            definition=SimpleNamespace(display_name="討伐魔物", key="hunt")
        )
        caller = Mock()
        caller.ndb.guild_request_pending = None

        result = _resolve_deferred(succeed(posted), caller)
        self.assertIs(result, posted)

        with self.assertRaises(NoSuitableTemplateError):
            _resolve_deferred(
                fail(NoSuitableTemplateError("none")), caller
            )

        pending = Deferred()
        caller.reset_mock()
        with self.assertRaises(_GuildRequestPendingError):
            _resolve_deferred(pending, caller)
        self.assertIs(caller.ndb.guild_request_pending, pending)

        pending.callback(posted)
        caller.msg.assert_called_with(
            "你張貼了一份委託：討伐魔物 （hunt）。用 guild list 查看。"
        )

    def test_resolve_pending_deferred_reports_named_and_generic_failures(self):
        from twisted.internet.defer import Deferred

        from commands.guild import _GuildRequestPendingError, _resolve_deferred
        from server.ai_director_service import NoSuitableTemplateError

        caller = Mock()
        caller.ndb.guild_request_pending = None
        pending = Deferred()
        with self.assertRaises(_GuildRequestPendingError):
            _resolve_deferred(pending, caller)
        pending.addErrback(lambda failure: None)
        pending.errback(NoSuitableTemplateError("none"))
        caller.msg.assert_called_with("公會目前沒有適合你的委託。")

        caller.reset_mock()
        pending = Deferred()
        with self.assertRaises(_GuildRequestPendingError):
            _resolve_deferred(pending, caller)
        pending.addErrback(lambda failure: None)
        pending.errback(RuntimeError("boom"))
        caller.msg.assert_called_with("委託未能完成，請稍後再試。")


class CombatCommandBranchTests(TestCase):
    def test_engage_validates_state_target_and_maps_every_rule_reason(self):
        command = _command(CmdEngage)
        with patch("commands.combat.is_in_active_session", return_value=True):
            command.func()
        command.caller.msg.assert_called_with("你已經在戰鬥中了。")

        expected = {
            SessionReason.NOT_HOSTILE: "這個目標不是敵對魔物。",
            SessionReason.NOT_PRESENT: "目標不在這裡。",
            SessionReason.TARGET_DEAD: "目標已經無法行動。",
            SessionReason.ALREADY_IN_COMBAT: "你已經在戰鬥中了。",
        }
        command.args = "enemy"
        command.caller.search.return_value = object()
        for reason, message in expected.items():
            command.caller.msg.reset_mock()
            with patch("commands.combat.is_in_active_session", return_value=False), patch(
                "commands.combat.engage", side_effect=CombatSessionError(reason)
            ):
                command.func()
            command.caller.msg.assert_called_with(message)

        command.caller.msg.reset_mock()
        with patch("commands.combat.is_in_active_session", return_value=False), patch(
            "commands.combat.engage",
            side_effect=CombatSessionError(SessionReason.NOT_A_PLAYER),
        ):
            command.func()
        command.caller.msg.assert_called_with("無法開始戰鬥。")

    def test_forfeit_maps_known_and_unknown_outcomes(self):
        for outcome, message in (
            ("defeat", "你投降了，戰鬥以失敗告終。"),
            ("exam_failed", "你放棄了考核。"),
            ("other", "戰鬥結束。"),
        ):
            command = _command(CmdCombatForfeit)
            with patch("commands.combat.forfeit", return_value={"outcome": outcome}):
                command.func()
            command.caller.msg.assert_called_with(message)

        command = _command(CmdCombatForfeit)
        with patch(
            "commands.combat.forfeit",
            side_effect=CombatSessionError(SessionReason.NO_ACTIVE_SESSION),
        ):
            command.func()
        command.caller.msg.assert_called_with("目前沒有進行中的戰鬥。")

    def test_exam_maps_every_rule_reason_and_success(self):
        expected = {
            ExamReason.UNREGISTERED: "你尚未註冊為冒險者。",
            ExamReason.WRONG_BRANCH: "考核官與你的公會不符。",
            ExamReason.NOT_NEXT_RANK: "你只能接受下一個階級的考核。",
            ExamReason.BELOW_THRESHOLD: "你的功績尚未達到考核門檻。",
            ExamReason.ACTIVE_COMBAT: "你已經在戰鬥中。",
            ExamReason.DUPLICATE_ACTIVE: "你已經有一場進行中的考核。",
            ExamReason.ALREADY_SETTLED: "你已經通過這個階級的考核。",
        }
        for reason, message in expected.items():
            command = _command(CmdGuildExam)
            command._resolve_examiner = Mock(return_value=object())
            with patch("commands.combat.start_guild_exam", side_effect=GuildExamError(reason)):
                command.func()
            command.caller.msg.assert_called_with(message)

        command = _command(CmdGuildExam)
        command._resolve_examiner = Mock(return_value=object())
        with patch(
            "commands.combat.start_guild_exam",
            side_effect=GuildExamError(ExamReason.NOT_A_PLAYER),
        ):
            command.func()
        command.caller.msg.assert_called_with("無法開始考核。")

        command = _command(CmdGuildExam, "D")
        command._resolve_examiner = Mock(return_value=object())
        with patch(
            "commands.combat.start_guild_exam",
            return_value=SimpleNamespace(target_rank="D"),
        ) as start:
            command.func()
        start.assert_called_once_with(command.caller, command._resolve_examiner.return_value, "D", requested_by="command")
        self.assertIn("D 階", command.caller.msg.call_args.args[0])


class EconomyCommandBranchTests(TestCase):
    def test_buy_and_sell_validate_input_and_map_rule_reasons(self):
        cases = (
            (CmdBuy, "buy", TradeReason.INSUFFICIENT_FUNDS, "你的銅幣不足。"),
            (CmdBuy, "buy", TradeReason.INSUFFICIENT_STOCK, "商店庫存不足。"),
            (CmdSell, "sell", TradeReason.UNSELLABLE, "這個物品無法販賣。"),
            (CmdSell, "sell", TradeReason.INSUFFICIENT_ITEMS, "你沒有足夠的這個物品。"),
            (CmdSell, "sell", TradeReason.STOCK_OVERFLOW, "商店收購上限已滿。"),
        )
        for command_type, function_name, reason, message in cases:
            command = _command(command_type, "meal 2")
            command.resolve_merchant = Mock(return_value=object())
            with patch(f"commands.economy.{function_name}", side_effect=TradeError(reason)):
                command.func()
            command.caller.msg.assert_called_with(message)

        for command_type in (CmdBuy, CmdSell):
            command = _command(command_type, "meal many")
            command.resolve_merchant = Mock(return_value=object())
            command.func()
            command.caller.msg.assert_called_with("數量必須是正整數。")

    def test_buy_and_sell_format_success(self):
        for command_type, function_name, verb in (
            (CmdBuy, "buy", "你買了 2 個 meal"),
            (CmdSell, "sell", "你賣了 2 個 meal"),
        ):
            command = _command(command_type, "meal 2")
            command.resolve_merchant = Mock(return_value=object())
            result = {"quantity": 2, "item_key": "meal", "total_copper": 20, "wallet": 80}
            with patch(f"commands.economy.{function_name}", return_value=result):
                command.func()
            self.assertIn(verb, command.caller.msg.call_args.args[0])

    def test_inventory_reports_wallet_empty_and_grouped_items(self):
        command = _command(CmdInventory)
        command.caller.db.wallet = None
        with patch("commands.economy.list_items", return_value=[]):
            command.func()
        self.assertEqual(
            [call.args[0] for call in command.caller.msg.call_args_list],
            ["錢包：0 銅", "背包是空的。"],
        )

        command.caller.msg.reset_mock()
        command.caller.db.wallet = 7
        with patch("commands.economy.list_items", return_value=["sword", "meal", "meal"]):
            command.func()
        self.assertEqual(command.caller.msg.call_args_list[0].args[0], "錢包：7 銅")
        self.assertEqual(command.caller.msg.call_args_list[1].args[0], "  meal ×2\n  sword ×1")
    def test_inventory_equipment_rows_carry_adjustment_prose(self):
        command = _command(CmdInventory)
        command.caller.db.wallet = 0
        with patch(
            "commands.economy.list_items",
            return_value=["knight_platemail", "healing_potion"],
        ):
            command.func()
        self.assertEqual(
            command.caller.msg.call_args_list[1].args[0],
            "  healing_potion ×1\n"
            "  knight_platemail ×1——攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15",
        )

    def test_stock_reports_missing_configuration_and_invalid_stock(self):
        host = Mock()
        host.components.get.return_value.shop_key = "missing"
        command = _command(CmdShopStock)
        command.resolve_merchant = Mock(return_value=host)
        with patch(
            "commands.economy.get_catalog", return_value=SimpleNamespace(shop_configs={})
        ):
            command.func()
        command.caller.msg.assert_called_with("這間商店沒有設定。")

        config = SimpleNamespace(offers=[])
        command.caller.msg.reset_mock()
        with patch(
            "commands.economy.get_catalog",
            return_value=SimpleNamespace(shop_configs={"missing": config}),
        ), patch("commands.economy.shop_is_open", return_value=False), patch(
            "commands.economy.parse_merchant_stock", side_effect=TradeError("corrupt")
        ):
            command.func()
        command.caller.msg.assert_called_with("商店資料有誤：corrupt")


class CharacterCreationCommandBranchTests(TestCase):
    def test_integer_rejects_cancel_and_non_integer(self):
        with self.assertRaisesRegex(CharacterCreationError, "角色建立已取消"):
            _integer(" cancel ", "age")
        with self.assertRaisesRegex(CharacterCreationError, "age 必須是整數"):
            _integer("old", "age")
        self.assertEqual(_integer(" 18 ", "age"), 18)

    def test_activate_reports_domain_error(self):
        command = _command(CmdCharacter)
        command.account = Mock()
        with patch(
            "commands.character_creation.activate_player_character",
            side_effect=CharacterCreationError("invalid"),
        ):
            command._activate(Mock())
        command.caller.msg.assert_called_with("角色建立失敗：invalid")

    def test_command_rejects_bad_preset_and_unknown_modes(self):
        command = _command(CmdCharacter, "preset")
        with self.assertRaises(StopIteration):
            next(command.func())
        command.caller.msg.assert_called_with("用法：character preset <key>")

        command = _command(CmdCharacter, "unknown")
        with self.assertRaises(StopIteration):
            next(command.func())
        command.caller.msg.assert_called_with("用法：character preset <key> 或 character create")

    def test_wizard_cancellation_at_name_race_subrace_and_confirmation(self):
        responses = (
            ["cancel"],
            ["name", "18", "18", "cancel"],
            ["name", "18", "18", "human", "cancel"],
        )
        for replies in responses:
            command = _command(CmdCharacter, "create")
            generator = command.func()
            next(generator)
            for reply in replies:
                try:
                    generator.send(reply)
                except StopIteration:
                    break
            command.caller.msg.assert_called_with("已取消角色建立。")

    def test_wizard_reports_invalid_integer(self):
        command = _command(CmdCharacter, "create")
        generator = command.func()
        next(generator)
        generator.send("name")
        with self.assertRaises(StopIteration):
            generator.send("old")
        self.assertIn("實際年齡 必須是整數", command.caller.msg.call_args.args[0])

    def test_wizard_non_yes_confirmation_cancels(self):
        command = _command(CmdCharacter, "create")
        profile = SimpleNamespace(bounds=(), budget=0)
        with patch("commands.character_creation.resolve_starting_profile", return_value=profile):
            generator = command.func()
            next(generator)
            generator.send("name")
            generator.send("18")
            generator.send("18")
            generator.send("human")
            generator.send("human_commoner")
            generator.send("")
            generator.send("")
            with self.assertRaises(StopIteration):
                generator.send("no")
        command.caller.msg.assert_called_with("已取消角色建立。")


class ActionCommandBranchTests(TestCase):
    def test_cast_validates_skill_and_missing_target(self):
        command = _command(CmdCast, "   ")
        command.func()
        command.caller.msg.assert_called_with("用法：cast <skill_key>[@<scale>][=<target_key>]")

        command = _command(CmdCast, "skill=missing")
        command._active_session = Mock(return_value=None)
        command.caller.search.return_value = None
        with patch("commands.action.settle_out_of_combat_cast") as settle:
            command.func()
        settle.assert_not_called()

    def test_session_cast_maps_errors_rejection_logs_and_terminal_outcome(self):
        command = _command(CmdCast)
        for reason, message in (
            (SessionReason.NO_ACTIVE_SESSION, "目前沒有進行中的戰鬥。"),
            (SessionReason.INVALID_RECOVERY, "你已經無法行動，戰鬥結束了。"),
            (SessionReason.NOT_PRESENT, "目標不在這裡。"),
        ):
            command.caller.msg.reset_mock()
            with patch(
                "world.rules.combat_session.submit_player_action",
                side_effect=CombatSessionError(reason),
            ):
                command._cast_in_session(object(), "skill", "")
            command.caller.msg.assert_called_with(message)

        command.caller.msg.reset_mock()
        with patch(
            "world.rules.combat_session.submit_player_action",
            return_value={"outcome": "rejected", "reason": object()},
        ):
            command._cast_in_session(object(), "skill", "")
        command.caller.msg.assert_called_with("這項行動無法完成。")

        command.caller.msg.reset_mock()
        with patch(
            "world.rules.combat_session.submit_player_action",
            return_value={"outcome": "victory", "logs": ["log"]},
        ), patch(
            "world.rules.combat_result.settle_to_messages",
            return_value=(("rendered",), "戰鬥結束，你取得了勝利。"),
        ):
            command._cast_in_session(object(), "skill", "")
        self.assertEqual(
            [call.args[0] for call in command.caller.msg.call_args_list],
            ["rendered", "戰鬥結束，你取得了勝利。"],
        )

    def test_out_of_combat_success_renders_from_the_settlement_and_failure_reports_reason(self):
        from world.rules.cast_settlement import CastSettlement

        command = _command(CmdCast)
        command.caller.ndb.action_context = object()
        success = SimpleNamespace(
            outcome="success", time_cost_seconds=5, event_log="log", reason=None
        )
        with patch(
            "commands.action.settle_out_of_combat_cast",
            return_value=CastSettlement(success, ()),
        ), patch("commands.action.render_plain_text", return_value="done"):
            command._cast_out_of_combat("skill", "")
        command.caller.msg.assert_called_with("done")

        command.caller.msg.reset_mock()
        failed = SimpleNamespace(outcome="rejected", reason=object())
        with patch(
            "commands.action.settle_out_of_combat_cast",
            return_value=CastSettlement(failed, ()),
        ):
            command._cast_out_of_combat("skill", "")
        command.caller.msg.assert_called_with("這項行動無法完成。")


class SkipCommandBranchTests(TestCase):
    def test_rest_rejects_bad_duration_and_unsafe_skip(self):
        command = _command(CmdRest, "tomorrow")
        command.func()
        command.caller.msg.assert_called_with("用法：rest <數字><s|m|h|d>")

        command = _command(CmdRest, "2h")
        with patch("commands.skip._safe_to_skip", return_value=False), patch(
            "commands.skip.get_world_clock"
        ) as clock:
            command.func()
        clock.assert_not_called()

    def test_sleep_advances_until_regenerated_and_reports_daily_reset(self):
        command = _command(CmdSleep)
        event = SimpleNamespace(kind="daily_reset")
        with patch("commands.skip._safe_to_skip", return_value=True), patch(
            "commands.skip._seconds_to_full_regen", return_value=90
        ), patch("commands.skip.get_world_clock") as clock:
            clock.return_value.advance.return_value = [event]
            command.func()
        clock.return_value.advance.assert_called_once()
        command.caller.msg.assert_called_with("時間經過了 90 秒。 新的一天開始了。")

    def test_wait_validates_syntax_daypart_and_safety(self):
        command = _command(CmdWaitUntil, "dawn")
        command.func()
        command.caller.msg.assert_called_with("用法：wait until <midnight|dawn|noon|dusk>")

        command = _command(CmdWaitUntil, "until nowhere")
        with patch("commands.skip.get_world_clock"), patch(
            "commands.skip.seconds_until_daypart", side_effect=DaypartError
        ):
            command.func()
        command.caller.msg.assert_called_with("未知的時段。")

        command = _command(CmdWaitUntil, "until dawn")
        with patch("commands.skip.get_world_clock") as clock, patch(
            "commands.skip.seconds_until_daypart", return_value=60
        ), patch("commands.skip._safe_to_skip", return_value=False):
            command.func()
        clock.return_value.advance.assert_not_called()

    def test_rest_reports_concrete_safety_rejection(self):
        command = _command(CmdRest, "5m")
        with patch(
            "commands.skip.evaluate_skip_safety",
            return_value=SkipRejectReason.HOSTILE_PRESENT,
        ), patch("commands.skip.get_world_clock") as clock:
            command.func()
        command.caller.msg.assert_called_with("附近有活著的怪物，這裡不安全。")
        clock.assert_not_called()

    def test_sleep_rejects_unsafe_skip_before_any_advance(self):
        command = _command(CmdSleep)
        with patch("commands.skip._safe_to_skip", return_value=False), patch(
            "commands.skip.get_world_clock"
        ) as clock:
            command.func()
        clock.assert_not_called()

    def test_wait_until_daypart_advances_and_reports_summary(self):
        command = _command(CmdWaitUntil, "until dawn")
        event = SimpleNamespace(kind="daily_reset")
        with patch("commands.skip._safe_to_skip", return_value=True), patch(
            "commands.skip.seconds_until_daypart", return_value=120
        ), patch("commands.skip.get_world_clock") as clock:
            clock.return_value.advance.return_value = [event]
            command.func()
        clock.return_value.advance.assert_called_once_with(
            120, AdvanceSource.SKIP, [command.caller]
        )
        command.caller.msg.assert_called_with("時間經過了 120 秒。 新的一天開始了。")
