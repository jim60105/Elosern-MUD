"""Integration tests for the pending character command boundary."""

from tools.spec_traceability import covers_requirement

from django.db import transaction
from unittest.mock import Mock, patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.character_creation import (
    ALLOCATION_AXIS_EXPLANATIONS,
    MAX_CONCEPT_LENGTH,
    CmdCharacter,
    CmdCharacterConcept,
    CharacterCreationCmdSet,
    creation_start_screen,
)
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.ai.character_creation import CharacterProposal


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
