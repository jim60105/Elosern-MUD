"""Slice of ``test_character_creation``: CharacterCreationCommandTests (wizard-activation half).
"""
from tools.spec_traceability import covers_requirement
from copy import replace
from django.db import transaction
from unittest.mock import Mock, patch
from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT
from evennia.utils.evmenu import CmdGetInput, InputCmdSet
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    resolve_starting_profile,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.lore.starting_kits import SubraceStartingKit
from world.tests.synthetic_data import (
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SUBRACES,
    _SYNTH_ELEMENT,
    make_subrace,
)
from commands.character_creation import (
    ALLOCATION_AXIS_EXPLANATIONS,
    MAX_CONCEPT_LENGTH,
    CmdCharacter,
    CmdCharacterConcept,
    CmdCreationRequired,
    CharacterCreationCmdSet,
    _age_prompt,
    _name_prompt,
    _proposal_summary,
    _terminal_safe,
    creation_start_screen,
)
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.ai.character_creation import CharacterProposal

from ._support import (
    QueuedDeferLater,
    _AFFINITY_BOUNDS,
    _BOUNDED_BRANCH,
    _BOUNDED_RACE,
    _ELF_BRANCH,
    _KIT_PRESET,
    _PRESET_COMMAND,
    _balanced_replies,
    _distinct_elements,
    _live_presets,
    _live_races,
    _messages,
    _open_creation_scope,
    _portrait_ensure_callbacks,
    _wizard_flow,
)


class CharacterCreationCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_creation_scope(self)
        super().setUp()
        self.account.at_post_create_character(self.char1)

    @covers_requirement("character-creation-ux::the-interactive-creation-wizard-collects-every-unmatched-reply")
    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_real_handler_cancel_reply_exits_wizard_and_tears_down_prompt(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd("character create", session=self.session)
                prompts = _messages(message_mock)
                self.assertTrue(any("角色姓名" in text for text in prompts))
                self.assertTrue(self.char1.ndb._getinput)
                self.assertTrue(self.char1.cmdset.has("input_cmdset"))
                self.char1.execute_cmd("cancel", session=self.session)
                queue.drain()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("已取消角色建立" in text for text in messages))
        self.assertTrue(self.char1.creation_pending)
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))

    @covers_requirement("character-creation-ux::the-interactive-creation-wizard-collects-every-unmatched-reply")
    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_real_handler_custom_wizard_completes_through_real_pipeline(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        replies = [
            *(_wizard_flow()),
        ]
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd("character create", session=self.session)
                for reply in replies:
                    self.char1.execute_cmd(reply, session=self.session)
                    queue.drain()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("已建立" in text for text in messages))
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.key, "自訂者")
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))

    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_real_handler_invalid_reply_reports_and_tears_down(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd("character create", session=self.session)
                for reply in ("自訂者", "abc"):
                    self.char1.execute_cmd(reply, session=self.session)
                    queue.drain()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("輸入無效" in text for text in messages))
        self.assertTrue(self.char1.creation_pending)
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))

    @covers_requirement("character-creation-ux::the-interactive-creation-wizard-collects-every-unmatched-reply")
    def test_reply_matching_gate_exposed_command_runs_the_command(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd("character create", session=self.session)
                self.assertTrue(self.char1.ndb._getinput)
                self.char1.execute_cmd("character", session=self.session)
                queue.drain()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("伊洛瑟恩大陸" in text for text in messages))
        self.assertTrue(self.char1.ndb._getinput)
        self.assertTrue(self.char1.cmdset.has("input_cmdset"))

    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_gate_rejects_empty_line_with_creation_required(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            self.char1.execute_cmd("", session=self.session)
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("先完成角色建立" in text for text in messages))

    @covers_requirement("character-creation-ux::the-character-creation-command-presents-preset-previews")
    def test_status_and_preset_activation(self):
        output = self.call(CmdCharacter(), "")
        self.assertIn("preset", output)
        self.assertIn("伊洛瑟恩大陸", output)
        for key, preset in _live_presets().items():
            self.assertIn(key, output)
            self.assertIn(preset.emphasis, output)
            self.assertIn(preset.persona.background, output)
        output = self.call(CmdCharacter(), f"preset {_KIT_PRESET}")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)
        self.char1.at_cmdset_get()
        self.assertFalse(self.char1.cmdset.has("CharacterCreation"))
        self.assertIsNotNone(self.char1.traits.magic_power)

    def test_creation_start_screen_is_registry_derived_and_reusable(self):
        screen = creation_start_screen()
        self.assertIn("你站在伊洛瑟恩大陸的門口", screen)
        for key, preset in _live_presets().items():
            self.assertIn(f"  {key}", screen)
            self.assertIn(preset.emphasis, screen)
            self.assertIn(preset.persona.background, screen)

    @covers_requirement("character-creation-ux::custom-creation-mode-explains-its-prompts")
    def test_custom_prompts_carry_explanations(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            replies = (
                [
                    "自訂者", "20", "20", _BOUNDED_RACE, _BOUNDED_BRANCH, "",
                    *_balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH), "",
                ]
            )
            prompts = [next(generator)]
            for reply in replies:
                prompts.append(generator.send(reply))
        finally:
            self.char1.msg = original_msg
        joined = "".join(prompts) + "".join(_messages(message_mock))
        for race in _live_races():
            self.assertIn(race, joined)
        for axis, explanation in ALLOCATION_AXIS_EXPLANATIONS.items():
            self.assertIn(axis, joined)
            self.assertIn(explanation, joined)
        # The scoped subrace rows' display names stand in for the shipped
        # branch labels the prompt renders from the registry.
        self.assertIn(SYNTH_SUBRACES[_BOUNDED_BRANCH].display_name_zh, joined)
        self.assertIn(SYNTH_SUBRACES[_BOUNDED_BRANCH].common_name_zh, joined)
        self.assertIn("配點說明", joined)
        self.assertIn("七項配點總和必須恰好等於", joined)
        self.assertIn("屬性親和", joined)
        self.assertIn("背景設定", joined)

    def test_custom_wizard_rejects_an_empty_or_unknown_subrace(self):
        for subrace in ("", "none", "t_unregistered_branch"):
            with self.subTest(subrace=subrace):
                command = CmdCharacter()
                command.caller = self.char1
                command.account = self.account
                command.args = "create"
                generator = command.func()
                replies = ["自訂者", "20", "20", _BOUNDED_RACE, subrace]
                next(generator)
                try:
                    for reply in replies:
                        generator.send(reply)
                except StopIteration:
                    pass
                self.assertTrue(self.char1.creation_pending)
                self.assertEqual(self.char1.traits.all(), [])

    def test_custom_wizard_collects_an_optional_background(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        replies = (
            ["自訂者", "20", "20", _BOUNDED_RACE, _BOUNDED_BRANCH]
            + [""]
            + _balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH)
            + ["在公會登記的新人冒險者", "yes"]
        )
        next(generator)
        for reply in replies:
            try:
                generator.send(reply)
            except StopIteration:
                break
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.db.persona["background"], "在公會登記的新人冒險者")

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_custom_wizard_collects_race_bounded_affinity(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        picked = _distinct_elements(_AFFINITY_BOUNDS[_BOUNDED_RACE])
        replies = (
            ["自訂者", "20", "20", _BOUNDED_RACE, _BOUNDED_BRANCH]
            + [" ".join(picked)]
            + _balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH)
            + ["", "yes"]
        )
        next(generator)
        for reply in replies:
            try:
                generator.send(reply)
            except StopIteration:
                break
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.db.affinity_elements, list(picked))

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_custom_wizard_rejects_an_over_bound_affinity_set(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        generator = command.func()
        bound = _AFFINITY_BOUNDS[_BOUNDED_RACE]
        first_two = _distinct_elements(bound)
        replies = (
            ["自訂者", "20", "20", _BOUNDED_RACE, _BOUNDED_BRANCH]
            + [" ".join([*first_two, first_two[0]])]
            + _balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH)
            + ["", "yes"]
        )
        try:
            next(generator)
            for reply in replies:
                generator.send(reply)
        except StopIteration:
            pass
        finally:
            self.char1.msg = original_msg
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        messages = [str(call.args[0]) for call in message_mock.call_args_list]
        self.assertTrue(
            any(f"最多只能選擇 {bound} 個屬性" in text for text in messages),
            messages,
        )

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_custom_wizard_skips_affinity_prompt_for_an_unbounded_race(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        replies = (
            ["暮行守", "180", "24", "elf", _ELF_BRANCH.key]
            + _balanced_replies("elf", _ELF_BRANCH.key)
            + ["", "yes"]
        )
        prompts = [next(generator)]
        for reply in replies:
            try:
                prompts.append(generator.send(reply))
            except StopIteration:
                break
        self.assertFalse(self.char1.creation_pending)
        # The unbounded race skips the prompt and the set seeds from the
        # chosen subrace row (the production elf rule).
        self.assertEqual(self.char1.db.affinity_elements, [_SYNTH_ELEMENT])
        joined = "".join(prompts)
        self.assertNotIn("屬性親和（可選擇", joined)

    def test_real_rest_reaches_clock_after_activation(self):
        self.call(CmdCharacter(), f"preset {_KIT_PRESET}")
        original_msg = self.char1.msg
        self.char1.msg = Mock()
        try:
            with patch("commands.skip.get_world_clock") as get_clock:
                get_clock.return_value.advance.return_value = []
                self.char1.execute_cmd("rest 5s", session=self.session)
            get_clock.return_value.advance.assert_called_once()
        finally:
            self.char1.msg = original_msg

    def test_custom_wizard_activates_the_existing_shell(self):
        old_id, old_location = self.char1.id, self.char1.location
        replies = [
            "自訂者", "20", "20", _BOUNDED_RACE, _BOUNDED_BRANCH,
            _SYNTH_ELEMENT, *_balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH),
            "背景文字", "yes",
        ]
        output = self.call(
            CmdCharacter(), "create", inputs=[*reversed(replies), None]
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "自訂者")
        self.assertEqual(self.char1.id, old_id)
        self.assertEqual(self.char1.location, old_location)
        self.assertIn(self.char1, self.account.characters)

    def test_abandoned_prompt_keeps_the_shell_unchanged(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        next(generator)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        self.assertIsNone(self.char1.age)
        self.assertIsNone(self.char1.apparent_age)

    def test_cancelled_custom_wizard_changes_nothing(self):
        old_key = self.char1.key
        output = self.call(CmdCharacter(), "create", inputs=["cancel", None])
        self.assertIn("已取消", output)
        self.assertEqual(self.char1.key, old_key)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])

    @covers_requirement("character-creation-ux::the-character-creation-restyle-does-not-change-activation-semantics")
    def test_restyled_custom_prompts_still_reject_age_below_zero(self):
        old_key = self.char1.key
        replies = [
            "新冒險者", "-1", "20", _BOUNDED_RACE, _BOUNDED_BRANCH,
            _SYNTH_ELEMENT, *_balanced_replies(_BOUNDED_RACE, _BOUNDED_BRANCH),
            "背景文字", "yes",
        ]
        output = self.call(
            CmdCharacter(), "create", inputs=[*reversed(replies), None]
        )
        self.assertIn("角色建立失敗", output)
        self.assertEqual(self.char1.key, old_key)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    def test_committed_creation_schedules_exactly_one_portrait_ensure(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            output = self.call(CmdCharacter(), _PRESET_COMMAND)
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(
            self.char1.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.char1.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # The retrofit: the committed creation owns one gallery job, never a
        # classic fixed-identity record.
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{self.char1.pk}:gen:")
        )
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    def test_rolled_back_creation_emits_no_job(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            output = self.call(
                CmdCharacter(),
                "create",
                inputs=["cancel", None],
            )
        self.assertIn("已取消", output)
        self.assertEqual(callbacks, [])
        self.assertIsNone(self.char1.db.portrait_policy)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_art_callback_exception_still_reports_creation_success(self):
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch(
                "world.art.service._ensure_gallery_subject",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            output = self.call(CmdCharacter(), _PRESET_COMMAND)
        self.assertIn("已建立", output)
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        self.assertFalse(self.char1.creation_pending)
