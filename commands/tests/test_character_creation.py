"""Integration tests for the pending character command boundary.

The real-handler end-to-end tests drive the wizard through the actual Evennia
cmdhandler with a queued ``deferLater`` fixture: the reactor's real ordering is
reply-command cleanup first (the handler deletes the old ``_getinput`` and
removes ``InputCmdSet``) and the deferred generator resume later (the wizard
mounts the next prompt). Draining the captured callbacks after each
``execute_cmd`` reproduces that cleanup-before-resume sequence. A synchronous
mock would instead resume the generator inside the reply command, and the
handler's trailing cleanup would wipe the freshly mounted next prompt.
"""

from tools.spec_traceability import covers_requirement

from django.db import transaction
from unittest.mock import Mock, patch

from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT
from evennia.utils.evmenu import CmdGetInput, InputCmdSet
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from world.rules.character_creation import CharacterCreationRequest

from commands.character_creation import (
    ALLOCATION_AXIS_EXPLANATIONS,
    MAX_CONCEPT_LENGTH,
    CmdCharacter,
    CmdCharacterConcept,
    CmdCreationRequired,
    CharacterCreationCmdSet,
    creation_start_screen,
)
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.ai.character_creation import CharacterProposal


class QueuedDeferLater:
    """Capture ``cmdhandler.deferLater`` calls instead of firing them.

    Each call appends ``(callback, args, kwargs)`` to a FIFO queue; ``drain``
    runs the captured callbacks in order. This preserves Evennia's real
    cleanup-before-resume ordering for progressive commands: the reply
    command's trailing teardown (``del _getinput`` + ``InputCmdSet`` removal)
    completes before the deferred ``_progressive_cmd_run`` resumes the wizard
    generator, so the newly mounted next prompt survives.
    """

    def __init__(self):
        self._calls = []

    def __call__(self, reactor, timedelay, callback, *args, **kwargs):
        self._calls.append((callback, args, kwargs))
        from twisted.internet import defer

        return defer.Deferred()

    def drain(self):
        while self._calls:
            callback, args, kwargs = self._calls.pop(0)
            callback(*args, **kwargs)

    def __enter__(self):
        self._patch = patch("evennia.commands.cmdhandler.deferLater", self)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()


def _prompt_stub(callback, prompt="角色姓名（輸入 cancel 取消）："):
    """A minimal stand-in for ``evmenu._Prompt``."""
    stub = Mock()
    stub._callback = callback
    stub._prompt = prompt
    stub._session = None
    stub._args = ()
    stub._kwargs = {}
    return stub


def _messages(message_mock):
    return [str(call.args[0]) for call in message_mock.call_args_list]


def _proposal(**overrides):
    payload = {
        "race_key": "human",
        "subrace_key": None,
        "allocations": {
            "hp": 100,
            "mp": 50,
            "sp": 0,
            "atk_phys": 10,
            "agility": 10,
            "defense": 11,
        },
        "suggested_skills": ("flight",),
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    payload.update(overrides)
    return CharacterProposal(**payload)


class CharacterCreationCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.at_post_create_character(self.char1)

    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_pending_gate_is_replace_and_blocks_world_commands(self):
        gate = CharacterCreationCmdSet(self.char1)
        self.assertEqual(gate.mergetype, "Replace")
        self.assertTrue(gate.no_exits)
        self.assertTrue(gate.no_objs)
        self.assertGreater(gate.priority, 10)
        self.char1.at_cmdset_get()
        self.assertTrue(self.char1.cmdset.has("CharacterCreation"))
        self.assertNotIn("rest", gate.get_all_cmd_keys_and_aliases(self.char1))
        self.assertIs(self.account.db._last_puppet, self.char1)
        self.assertTrue(self.char1.locks.check(self.account, "puppet"))

    def test_real_command_handler_rejects_rest_before_clock_access(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with patch("commands.skip.get_world_clock") as clock:
                self.char1.execute_cmd("rest 5s", session=self.session)
            messages = " ".join(str(call.args[0]) for call in message_mock.call_args_list)
        finally:
            self.char1.msg = original_msg
        self.assertIn("先完成角色建立", messages)
        clock.assert_not_called()

    def test_real_command_handler_blocks_exit_object_and_combat_commands(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        old_location = self.char1.location
        old_object_location = self.obj1.location
        try:
            for raw in (self.exit.key, f"get {self.obj1.key}", "engage"):
                self.char1.execute_cmd(raw, session=self.session)
        finally:
            self.char1.msg = original_msg
        self.assertEqual(self.char1.location, old_location)
        self.assertEqual(self.obj1.location, old_object_location)
        messages = " ".join(str(call.args[0]) for call in message_mock.call_args_list)
        self.assertGreaterEqual(messages.count("先完成角色建立"), 3)

    def test_pending_gate_reappears_from_persistent_state(self):
        self.char1.at_cmdset_get()
        self.char1.cmdset.remove("CharacterCreation")
        self.char1.attributes.reset_cache()
        self.assertTrue(self.char1.creation_pending)
        self.char1.at_cmdset_get()
        self.assertTrue(self.char1.cmdset.has("CharacterCreation"))

    def test_merged_cmdset_gate_wins_prompt_command_dedup(self):
        merged = InputCmdSet(self.char1) + CharacterCreationCmdSet(self.char1)
        nomatch = merged.get(CMD_NOMATCH)
        self.assertIsInstance(nomatch, CmdCreationRequired)
        self.assertFalse(any(isinstance(cmd, CmdGetInput) for cmd in merged.commands))
        noinput = merged.get(CMD_NOINPUT)
        self.assertIsInstance(noinput, CmdCreationRequired)

    def test_gate_handler_forwards_open_prompt_reply_and_cleans_up(self):
        callback = Mock(return_value=False)
        self.char1.ndb._getinput = _prompt_stub(callback)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "自訂者"
        command.func()
        callback.assert_called_once_with(
            self.char1, "角色姓名（輸入 cancel 取消）：", "自訂者"
        )
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))

    def test_gate_handler_keeps_prompt_state_when_callback_returns_truthy(self):
        callback = Mock(return_value=True)
        self.char1.ndb._getinput = _prompt_stub(callback)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "再試"
        command.func()
        callback.assert_called_once_with(
            self.char1, "角色姓名（輸入 cancel 取消）：", "再試"
        )
        self.assertTrue(self.char1.ndb._getinput)
        self.assertTrue(self.char1.cmdset.has("input_cmdset"))

    def test_gate_handler_no_prompt_keeps_creation_required_message(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            command = CmdCreationRequired()
            command.caller = self.char1
            command.raw_string = "rest 5s"
            command.func()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("先完成角色建立" in text for text in messages))
        self.assertFalse(self.char1.ndb._getinput)

    def test_gate_handler_cleans_up_when_callback_raises(self):
        def boom(caller, prompt, result):
            raise RuntimeError("boom")

        self.char1.ndb._getinput = _prompt_stub(boom)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with patch("commands.character_creation.logger.log_trace") as log_trace:
                command = CmdCreationRequired()
                command.caller = self.char1
                command.session = self.session
                command.raw_string = "x"
                command.func()
        finally:
            self.char1.msg = original_msg
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))
        log_trace.assert_called_once()
        messages = _messages(message_mock)
        self.assertTrue(any("Error in get_input" in text for text in messages))

    def test_gate_handler_routes_account_level_prompt(self):
        def callback(caller, prompt, result):
            self.assertIs(
                caller, self.account, "account-level prompt routes with the account as caller"
            )
            self.assertIs(
                caller.ndb._getinput._session,
                command.session,
                "the account prompt's session is recorded on the account",
            )
            return False

        self.account.ndb._getinput = _prompt_stub(callback)
        self.account.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "cancel"
        command.func()
        self.assertFalse(self.account.ndb._getinput)
        self.assertFalse(self.account.cmdset.has("input_cmdset"))

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
            "自訂者", "20", "20", "human", "",
            "100", "50", "31", "0", "0", "0", "yes",
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
        for key, preset in PLAYER_PRESET_REGISTRY.items():
            self.assertIn(key, output)
            self.assertIn(preset.emphasis, output)
            self.assertIn(preset.background, output)
        output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)
        self.char1.at_cmdset_get()
        self.assertFalse(self.char1.cmdset.has("CharacterCreation"))
        self.assertIsNotNone(self.char1.traits.magic_level)

    def test_creation_start_screen_is_registry_derived_and_reusable(self):
        screen = creation_start_screen()
        self.assertIn("你站在伊洛瑟恩大陸的門口", screen)
        for key, preset in PLAYER_PRESET_REGISTRY.items():
            self.assertIn(f"  {key}", screen)
            self.assertIn(preset.emphasis, screen)
            self.assertIn(preset.background, screen)

    @covers_requirement("character-creation-ux::custom-creation-mode-explains-its-prompts")
    def test_custom_prompts_carry_explanations(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        replies = ["自訂者", "20", "20", "human", "none"] + ["0"] * 6
        prompts = [next(generator)]
        for reply in replies:
            prompts.append(generator.send(reply))
        joined = "".join(prompts)
        for race in ("human", "beastfolk", "elf"):
            self.assertIn(race, joined)
        for axis, explanation in ALLOCATION_AXIS_EXPLANATIONS.items():
            self.assertIn(axis, joined)
            self.assertIn(explanation, joined)

    def test_real_rest_reaches_clock_after_activation(self):
        self.call(CmdCharacter(), "preset human_wanderer")
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
            "自訂者", "20", "20", "human", "none",
            "100", "50", "31", "0", "0", "0", "yes",
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
    def test_restyled_custom_prompts_still_reject_age_17(self):
        old_key = self.char1.key
        replies = [
            "新冒險者", "17", "20", "human", "none",
            "100", "50", "31", "0", "0", "0", "yes",
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
            output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(
            self.char1.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.char1.pk)},
        )
        self.assertEqual(len(callbacks), 1)
        records = ArtAssetRecord.objects.filter(
            db_key=f"art:portrait:character:{self.char1.pk}"
        )
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.PENDING)

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
                "world.art.service._ensure_character_portrait",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(self.char1.creation_pending)


def _fired_deferred(value):
    from twisted.internet import defer

    return defer.succeed(value)


class CharacterConceptCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.at_post_create_character(self.char1)
        self._patch = patch(
            "commands.character_creation.request_character_proposal"
        )

    def _propose(self, proposal):
        patch_obj = self._patch.start()
        patch_obj.return_value = _fired_deferred(proposal)
        self.addCleanup(self._patch.stop)
        return patch_obj

    def _degrade(self):
        patch_obj = self._patch.start()
        patch_obj.return_value = _fired_deferred(None)
        self.addCleanup(self._patch.stop)
        return patch_obj

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_concept_guides_an_interactive_custom_activation(self):
        self._propose(_proposal())
        replies = ["自訂者", "20", "20"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("角色提案", output)
        self.assertIn("human", output)
        self.assertIn("flight", output)
        self.assertIn("沉穩", output)
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "自訂者")
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.age, 20)
        self.assertEqual(self.char1.apparent_age, 20)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_concept_alias_構想_reaches_the_same_flow(self):
        self._propose(_proposal())
        replies = ["自訂者", "20", "20"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已建立", output)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_concept_path_cannot_bypass_the_adult_gate(self):
        self._propose(_proposal())
        replies = ["新冒險者", "17", "20"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("角色建立失敗", output)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        self.assertIsNone(self.char1.age)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_concept_path_cannot_bypass_the_apparent_adult_gate(self):
        self._propose(_proposal())
        replies = ["新冒險者", "20", "17"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("角色建立失敗", output)
        self.assertTrue(self.char1.creation_pending)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_empty_and_over_bound_concepts_are_rejected_before_any_call(self):
        patch_obj = self._patch.start()
        self.addCleanup(self._patch.stop)
        output = self.call(CmdCharacterConcept(), "")
        self.assertIn("用法", output)
        patch_obj.assert_not_called()
        output = self.call(
            CmdCharacterConcept(), "構想 " + "長" * (MAX_CONCEPT_LENGTH + 1)
        )
        self.assertIn("構想過長", output)
        patch_obj.assert_not_called()
        self.assertTrue(self.char1.creation_pending)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_offline_degrade_returns_the_stable_message_and_changes_no_state(self):
        self._degrade()
        old_key = self.char1.key
        output = self.call(CmdCharacterConcept(), "構想 流浪的精靈劍士")
        self.assertIn("生成不可用，請手動創角", output)
        self.assertEqual(self.char1.key, old_key)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        self.assertIsNone(self.char1.db.portrait_policy)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_every_profile_failing_still_keeps_deterministic_creation_usable(self):
        from django.test import override_settings

        from world.ai import guardrail
        from world.ai.character_creation import register_character_creation
        from world.ai.schemas.registry import _OUTPUT_SCHEMAS
        from world.ai.profiles import default_profiles

        guardrail._semantic_validators.clear()
        guardrail._degrade_fallbacks.clear()
        _OUTPUT_SCHEMAS.clear()
        register_character_creation()
        raw = default_profiles()
        for values in raw.values():
            values["enabled"] = False
        self.addCleanup(guardrail._semantic_validators.clear)
        self.addCleanup(guardrail._degrade_fallbacks.clear)
        self.addCleanup(_OUTPUT_SCHEMAS.clear)
        with override_settings(LLM_PROFILES=raw):
            output = self.call(CmdCharacterConcept(), "構想 流浪的精靈劍士")
        self.assertIn("生成不可用，請手動創角", output)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_cancel_within_the_concept_flow_changes_nothing(self):
        self._propose(_proposal())
        replies = ["cancel", None]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已取消", output)
        self.assertTrue(self.char1.creation_pending)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_deterministic_preset_and_custom_flows_still_work(self):
        output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_proposal_values_reach_the_ordinary_preflight(self):
        self._propose(
            _proposal(
                race_key="elf",
                subrace_key="fionnen",
                allocations={
                    "hp": 0,
                    "mp": 0,
                    "sp": 0,
                    "atk_phys": 12,
                    "agility": 12,
                    "defense": 13,
                },
            )
        )
        replies = ["瑟芮雅", "180", "24"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 長壽的精靈守護者",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.race, "elf")
        self.assertEqual(self.char1.subrace, "fionnen")
        self.assertEqual(self.char1.age, 180)

    def test_concept_bound_parity_with_the_layer(self):
        from world.ai.character_creation import MAX_CONCEPT_LENGTH as layer_bound

        self.assertEqual(MAX_CONCEPT_LENGTH, layer_bound)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_concept_flow_saves_the_draft_and_persists_persona_at_activation(self):
        from world.rules.creation_wizard import read_draft

        self._propose(_proposal())
        replies = ["自訂者", "20", "20"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已建立", output)
        # The activation cleared the draft and persisted the persona in the
        # import-card shape through the same all-or-nothing transaction.
        self.assertIsNone(read_draft(self.char1))
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.db.persona["personality"], "沉穩")
        self.assertEqual(self.char1.db.persona["life_story"], "來自邊境的小村")
        self.assertEqual(self.char1.db.persona["habit"], "清晨練劍")
        for key in ("identity", "appearance", "social_connection"):
            self.assertEqual(self.char1.db.persona[key], {})

    @covers_requirement("creation-persona-persistence::concept-apply-is-deterministic-and-fingerprint-protected")
    def test_stale_concept_draft_reports_and_changes_no_state(self):
        from twisted.internet import defer

        from world.rules.creation_wizard import read_draft, save_custom_draft

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 流浪的精靈劍士"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            with self.assertRaises(StopIteration):
                next(generator)
            # Another entry changes the draft while the proposal is in flight.
            save_custom_draft(
                self.account, self.char1,
                CharacterCreationRequest(
                    mode="custom", display_name="其他角色", age=20,
                    apparent_age=20, race="human", subrace=None,
                    allocations={
                        "hp": 50, "mp": 50, "sp": 50,
                        "atk_phys": 10, "agility": 10, "defense": 11,
                    },
                ),
            )
            held.callback(_proposal())
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertTrue(
                any("構想草稿已被修改" in text for text in messages),
                messages,
            )
            self.assertEqual(read_draft(self.char1)["mode"], "custom")
            self.assertTrue(self.char1.creation_pending)
        finally:
            self.char1.msg = original_msg

    @covers_requirement("creation-persona-persistence::a-server-owned-concept-draft-stores-the-validated-proposal-and-persona-block")
    @covers_requirement("creation-persona-persistence::concept-apply-is-deterministic-and-fingerprint-protected")
    def test_draft_replaced_during_prompts_rejects_activation(self):
        from twisted.internet import defer

        from world.rules.creation_wizard import read_draft, save_custom_draft

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 流浪的精靈劍士"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            with self.assertRaises(StopIteration):
                next(generator)
            held.callback(_proposal())
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertTrue(any("角色提案" in text for text in messages))
            self.assertEqual(read_draft(self.char1)["mode"], "concept")
            self.char1.execute_cmd("自訂者", session=self.session)
            # Another entry replaces the draft while the age prompts are open.
            save_custom_draft(
                self.account, self.char1,
                CharacterCreationRequest(
                    mode="custom", display_name="其他角色", age=20,
                    apparent_age=20, race="human", subrace=None,
                    allocations={
                        "hp": 50, "mp": 50, "sp": 50,
                        "atk_phys": 10, "agility": 10, "defense": 11,
                    },
                ),
            )
            self.char1.execute_cmd("20", session=self.session)
            self.char1.execute_cmd("20", session=self.session)
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertTrue(
                any("構想草稿已被修改" in text for text in messages),
                messages,
            )
            self.assertTrue(self.char1.creation_pending)
            self.assertEqual(read_draft(self.char1)["mode"], "custom")
            self.assertIsNone(self.char1.age)
            self.assertNotEqual(self.char1.key, "自訂者")
        finally:
            self.char1.msg = original_msg

    def test_cancel_after_apply_keeps_the_concept_draft_for_resume(self):
        from world.rules.creation_wizard import read_draft

        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=["cancel", None],
        )
        self.assertIn("已取消", output)
        self.assertTrue(self.char1.creation_pending)
        draft = read_draft(self.char1)
        self.assertEqual(draft["mode"], "concept")
        self.assertEqual(draft["persona"]["personality"], "沉穩")
        self.assertEqual(self.char1.traits.all(), [])
        self.assertIsNone(self.char1.age)

    @covers_requirement("character-creation-ux::the-interactive-creation-wizard-collects-every-unmatched-reply")
    def test_real_handler_sync_concept_continuation_reaches_prompts(self):
        self._propose(_proposal())
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd(
                    "character concept 流浪的精靈劍士", session=self.session
                )
                prompts = _messages(message_mock)
                self.assertTrue(any("角色提案" in text for text in prompts))
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

    def test_live_async_proposal_continues_interactively_when_it_fires(self):
        from twisted.internet import defer

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 流浪的精靈劍士"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            with self.assertRaises(StopIteration):
                next(generator)
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertIn("正在生成角色提案，請稍候……", messages)
            held.callback(_proposal())
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertTrue(any("角色提案" in text for text in messages))
            self.assertTrue(any("角色姓名" in text for text in messages))
            self.char1.execute_cmd("自訂者", session=self.session)
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertTrue(any("實際年齡" in text for text in messages))
            self.char1.execute_cmd("20", session=self.session)
            self.char1.execute_cmd("20", session=self.session)
            self.assertFalse(self.char1.creation_pending)
            self.assertEqual(self.char1.key, "自訂者")
            self.assertFalse(self.char1.cmdset.has("ConceptPrompt"))
        finally:
            self.char1.msg = original_msg

    def test_stale_proposal_after_activation_is_ignored(self):
        from twisted.internet import defer

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 流浪的精靈劍士"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            with self.assertRaises(StopIteration):
                next(generator)
            output = self.call(CmdCharacter(), "preset human_wanderer")
            self.assertIn("已建立", output)
            self.assertFalse(self.char1.creation_pending)
            held.callback(_proposal())
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertIn("生成不可用，請手動創角", messages)
            self.assertFalse(self.char1.cmdset.has("ConceptPrompt"))
            self.assertNotIn("角色提案", messages)
        finally:
            self.char1.msg = original_msg
