"""Slice of ``test_character_creation``: CharacterConceptCommandTests.
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
    _BOUNDED_BRANCH,
    _BOUNDED_RACE,
    _ConceptFixtureMixin,
    _ELF_BRANCH,
    _KIT_PRESET,
    _PRESET_COMMAND,
    _balanced_replies,
    _messages,
    _proposal,
)


class CharacterConceptCommandTests(_ConceptFixtureMixin, EvenniaCommandTestMixin, EvenniaTest):
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
        self.assertIn(_BOUNDED_RACE, output)
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
    def test_concept_path_cannot_bypass_the_age_range_check(self):
        self._propose(_proposal())
        replies = ["新冒險者", "-1", "20"]
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
    def test_concept_path_cannot_bypass_the_apparent_age_range_check(self):
        self._propose(_proposal())
        replies = ["新冒險者", "20", "-1"]
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
        output = self.call(CmdCharacter(), _PRESET_COMMAND)
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
        output = self.call(CmdCharacter(), _PRESET_COMMAND)
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_proposal_values_reach_the_ordinary_preflight(self):
        self._propose(
            _proposal(
                race_key="elf",
                subrace_key=_ELF_BRANCH.key,
                allocations=dict(
                    zip(
                        ALLOCATABLE_AXES,
                        (int(v) for v in _balanced_replies("elf", _ELF_BRANCH.key)),
                    )
                ),
            )
        )
        replies = ["暮行守", "180", "24"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 長壽的精靈守護者",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.race, "elf")
        self.assertEqual(self.char1.subrace, _ELF_BRANCH.key)
        self.assertEqual(self.char1.age, 180)

    def test_concept_bound_parity_with_the_layer(self):
        from world.ai.character_creation import MAX_CONCEPT_LENGTH as layer_bound

        self.assertEqual(MAX_CONCEPT_LENGTH, layer_bound)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_concept_flow_persists_persona_at_activation(self):
        from world.rules.creation_wizard import read_draft

        self._propose(_proposal())
        replies = ["自訂者", "20", "20"]
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=[*reversed(replies), None],
        )
        self.assertIn("已建立", output)
        # The transient flow persisted nothing before activation; the
        # persona block rode the request into the import-card shape inside
        # the same all-or-nothing transaction (retool-concept-transient-fill
        # D6).
        self.assertIsNone(read_draft(self.char1))
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.db.persona["personality"], "沉穩")
        self.assertEqual(self.char1.db.persona["life_story"], "來自邊境的小村")
        self.assertEqual(self.char1.db.persona["habit"], "清晨練劍")
        for key in ("identity", "appearance", "social_connection"):
            self.assertEqual(self.char1.db.persona[key], {})

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_draft_from_another_entry_never_mixes_into_the_concept_flow(self):
        # The concept flow reads and writes no draft: another entry saving a
        # custom draft mid-prompt neither blocks nor feeds activation. The
        # activation uses the proposal's values and persona only, and the
        # atomic activation clears any leftover draft.
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
            self.assertIsNone(read_draft(self.char1))
            self.char1.execute_cmd("自訂者", session=self.session)
            # Another entry replaces the draft while the age prompts are open.
            save_custom_draft(
                self.account, self.char1,
                CharacterCreationRequest(
                    mode="custom", display_name="其他角色", age=20,
                    apparent_age=20, race=_BOUNDED_RACE, subrace=_BOUNDED_BRANCH,
                    allocations=dict(SYNTH_PRESETS[_KIT_PRESET].allocations),
                ),
            )
            self.char1.execute_cmd("20", session=self.session)
            self.char1.execute_cmd("20", session=self.session)
            self.assertFalse(self.char1.creation_pending)
            self.assertEqual(self.char1.key, "自訂者")
            self.assertEqual(self.char1.age, 20)
            # The foreign draft is cleared by the same atomic activation and
            # its identity values never mixed into the character.
            self.assertIsNone(read_draft(self.char1))
            self.assertEqual(self.char1.race, _BOUNDED_RACE)
            self.assertEqual(self.char1.db.persona["personality"], "沉穩")
        finally:
            self.char1.msg = original_msg

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_cancel_after_proposal_persists_nothing(self):
        from world.rules.creation_wizard import read_draft

        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=["cancel", None],
        )
        self.assertIn("已取消", output)
        self.assertTrue(self.char1.creation_pending)
        # A transient apply persists nothing: cancelling after the summary
        # leaves no draft and no persona (retool-concept-transient-fill D6).
        self.assertIsNone(read_draft(self.char1))
        self.assertFalse(self.char1.attributes.has("persona"))
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
            output = self.call(CmdCharacter(), _PRESET_COMMAND)
            self.assertIn("已建立", output)
            self.assertFalse(self.char1.creation_pending)
            held.callback(_proposal())
            messages = [call.args[0] for call in message_mock.call_args_list]
            self.assertIn("生成不可用，請手動創角", messages)
            self.assertFalse(self.char1.cmdset.has("ConceptPrompt"))
            self.assertNotIn("角色提案", messages)
        finally:
            self.char1.msg = original_msg
