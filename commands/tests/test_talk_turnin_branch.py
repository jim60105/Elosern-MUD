"""Focused behavior tests for the talk command's dialogue turn-in surface.

Pure-logic branch tests mirroring ``test_command_branch_behaviour.py``: the
``回報`` keyword on a ``guild_staff`` dialogue host routes to
``dialogue_turn_in`` when a quest id follows, and otherwise flows through the
shared deterministic talk writer (``run_scripted_talk``) resolution unchanged.
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from commands.talk import CmdsTalk
from world.onboarding.guide_dialogue import (
    GUARD_DIALOGUE_KEY,
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
)
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    RewardClaimError,
)
from world.rules.onboarding import ScriptedTalkResult

_NO_RESPONSE = "對方沒有理會你。"


def _command(args: str) -> CmdsTalk:
    command = CmdsTalk()
    command.caller = Mock()
    command.args = args
    return command


def _staff_npc():
    npc = Mock()
    npc.key = "公會職員"
    npc.components.has.return_value = True
    return npc


class TalkTurnInBranchTests(TestCase):
    def test_turnin_with_quest_id_on_guild_staff_calls_the_service(self):
        command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1")
        npc = _staff_npc()
        with patch("commands.talk._resolve_npc", return_value=npc), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.dialogue_turn_in",
            return_value={
                "quest_id": "quest-1",
                "copper": 50,
                "merit": 25,
                "items": ["healing_potion"],
                "onboarding_completed": False,
            },
        ) as turnin, patch("commands.talk.run_scripted_talk") as response:
            command.func()
        turnin.assert_called_once_with(command.caller, npc, "quest-1")
        response.assert_not_called()
        self.assertIn("你回報了任務 quest-1", command.caller.msg.call_args.args[0])

    def test_turnin_reports_onboarding_completion_line(self):
        command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1")
        with patch("commands.talk._resolve_npc", return_value=_staff_npc()), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.dialogue_turn_in",
            return_value={
                "quest_id": "quest-1",
                "copper": 0,
                "merit": 0,
                "items": [],
                "onboarding_completed": True,
            },
        ):
            command.func()
        self.assertEqual(
            command.caller.msg.call_args_list[1].args[0],
            "你的第一個日子在這裡圓滿結束。冒險者，歡迎正式踏入伊洛瑟恩大陸。",
        )

    def test_turnin_maps_reward_and_data_errors(self):
        npc = _staff_npc()
        for error in (RewardClaimError("already_claimed"), GuildDataError("bad")):
            command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1")
            with patch("commands.talk._resolve_npc", return_value=npc), patch(
                "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
            ), patch("commands.talk.dialogue_turn_in", side_effect=error):
                command.func()
            self.assertIn(
                "無法回報任務", command.caller.msg.call_args.args[0]
            )

    def test_turnin_keyword_without_quest_id_flows_through_talk_writer(self):
        command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        npc = _staff_npc()
        with patch("commands.talk._resolve_npc", return_value=npc), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.run_scripted_talk",
            return_value=ScriptedTalkResult(
                response="「目前沒有可以交回的任務。」", budget_capped=False
            ),
        ) as response, patch(
            "commands.talk.dialogue_turn_in"
        ) as turnin:
            command.func()
        turnin.assert_not_called()
        response.assert_called_once_with(npc, command.caller, GUILD_STAFF_TURNIN_KEYWORD)
        command.caller.msg.assert_called_once_with(
            f"{npc.key}說：「目前沒有可以交回的任務。」"
        )

    def test_turnin_keyword_on_non_guild_host_is_a_plain_keyword(self):
        npc = Mock()
        npc.key = "南門守衛"
        for args in (
            f"南門守衛 {GUILD_STAFF_TURNIN_KEYWORD}",
            f"南門守衛 {GUILD_STAFF_TURNIN_KEYWORD} quest-1",
        ):
            command = _command(args)
            with patch("commands.talk._resolve_npc", return_value=npc), patch(
                "commands.talk.dialogue_key_for", return_value=GUARD_DIALOGUE_KEY
            ), patch("commands.talk.run_scripted_talk", return_value=None) as response, patch(
                "commands.talk.dialogue_turn_in"
            ) as turnin:
                command.func()
            turnin.assert_not_called()
            response.assert_called_once_with(npc, command.caller, command.args.partition(" ")[2].strip())
            command.caller.msg.assert_called_once_with(_NO_RESPONSE)

    def test_turnin_keyword_on_staff_table_without_staff_component_is_plain(self):
        # A non-staff NPC reusing the guild_staff table (e.g. a bard) must not
        # enter the turn-in branch: the full keyword stays an unknown keyword.
        npc = Mock()
        npc.key = "吟遊詩人"
        npc.components.has.return_value = False
        command = _command(f"吟遊詩人 {GUILD_STAFF_TURNIN_KEYWORD} quest-1")
        with patch("commands.talk._resolve_npc", return_value=npc), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch("commands.talk.run_scripted_talk", return_value=None) as response, patch(
            "commands.talk.dialogue_turn_in"
        ) as turnin:
            command.func()
        turnin.assert_not_called()
        response.assert_called_once_with(npc, command.caller, "回報 quest-1")
        command.caller.msg.assert_called_once_with(_NO_RESPONSE)

    def test_host_resolution_failure_renders_the_standard_rejection_line(self):
        command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1")
        with patch("commands.talk._resolve_npc", return_value=_staff_npc()), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.dialogue_turn_in", side_effect=GuildServiceError("multiple")
        ):
            command.func()
        command.caller.msg.assert_called_once_with("這裡沒有公會服務人員。")

    def test_talk_writer_errors_on_turnin_keyword_are_reported(self):
        command = _command(f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        with patch("commands.talk._resolve_npc", return_value=_staff_npc()), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.run_scripted_talk", side_effect=RewardClaimError("malformed_claims")
        ):
            command.func()
        self.assertIn(
            "無法回報任務：malformed_claims", command.caller.msg.call_args.args[0]
        )

    def test_other_keywords_are_untouched(self):
        npc = _staff_npc()
        command = _command("公會職員 公會")
        with patch("commands.talk._resolve_npc", return_value=npc), patch(
            "commands.talk.dialogue_key_for", return_value=GUILD_STAFF_DIALOGUE_KEY
        ), patch(
            "commands.talk.run_scripted_talk",
            return_value=ScriptedTalkResult(response="公會回應", budget_capped=False),
        ) as response, patch(
            "commands.talk.dialogue_turn_in"
        ) as turnin:
            command.func()
        turnin.assert_not_called()
        response.assert_called_once_with(npc, command.caller, "公會")
        command.caller.msg.assert_called_once_with(f"{npc.key}說：公會回應")
