"""Slice of ``test_character_creation``: CharacterConceptPrefillTests.
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
    _ConceptFixtureMixin,
    _PRESET_COMMAND,
    _element_display,
    _messages,
    _proposal,
    _stack,
)


class CharacterConceptPrefillTests(_ConceptFixtureMixin, EvenniaCommandTestMixin, EvenniaTest):
    """Prefilled-default prompts (prefill-telnet-concept-from-proposal).

    Every test pins one edge of the proposal-prefill contract: Enter accepts
    the named default, a typed reply overrides it, an absent field stays
    mandatory (the name re-prompts on a blank reply), and the proposal's
    background/affinity ride the activation request through the unchanged
    deterministic preflight.
    """

    _FULL = {
        "display_name": "雪貓",
        "age": 20,
        "apparent_age": 19,
        "background": "邊境孤兒，被商隊收養",
        "affinity_elements": (_SYNTH_ELEMENT,),
    }

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_empty_replies_accept_every_prefilled_default(self):
        self._propose(_proposal(**self._FULL))
        output = self.call(
            CmdCharacterConcept(),
            "構想 一個貓人少女",
            inputs=_stack("", "", ""),
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "雪貓")
        self.assertEqual(self.char1.age, 20)
        self.assertEqual(self.char1.apparent_age, 19)
        self.assertEqual(self.char1.db.affinity_elements, [_SYNTH_ELEMENT])
        self.assertEqual(
            self.char1.db.persona["background"], "邊境孤兒，被商隊收養"
        )
        self.assertFalse(self.char1.creation_pending)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_typed_replies_override_prefilled_defaults(self):
        self._propose(_proposal(**self._FULL))
        # Distinguishable replies: typed name, Enter age, typed apparent age.
        output = self.call(
            CmdCharacterConcept(),
            "構想 一個貓人少女",
            inputs=_stack("自訂名", "", "22"),
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "自訂名")
        self.assertEqual(self.char1.age, 20)
        self.assertEqual(self.char1.apparent_age, 22)
        # The untouched proposal values still flow through unchanged.
        self.assertEqual(self.char1.db.affinity_elements, [_SYNTH_ELEMENT])
        self.assertEqual(
            self.char1.db.persona["background"], "邊境孤兒，被商隊收養"
        )

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_typed_name_whitespace_is_owned_by_the_rules_validator(self):
        self._propose(_proposal(**self._FULL))
        # Typed padded name first, Enter on the ages.
        output = self.call(
            CmdCharacterConcept(),
            "構想 一個貓人少女",
            inputs=_stack("  帶邊空白名  ", "", ""),
        )
        self.assertIn("已建立", output)
        # The raw reply rides the request; the rules-layer validator owns the
        # strip (unchanged ownership from the pre-prefill flow).
        self.assertEqual(self.char1.key, "帶邊空白名")
        self.assertEqual(self.char1.age, 20)
        self.assertEqual(self.char1.apparent_age, 19)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_absent_name_blank_reply_re_prompts_until_a_name_or_cancel(self):
        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("", "   ", "自訂者", "20", "20"),
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "自訂者")
        # The blank replies re-prompted instead of ending the flow: accepting
        # either one as the name would have reached preflight empty and doomed
        # the activation, and the age replies would have been misaligned. The
        # prompt texts themselves are asserted through the production-rack
        # tests below (the call harness discards yielded prompts).

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_padded_cancel_during_the_mandatory_name_aborts_cleanly(self):
        # Padded cancellation parses identically on the name and age prompts
        # (both strip + lower the reply before matching).
        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack(" CANCEL "),
        )
        self.assertIn("已取消", output)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_clamped_default_age_is_accepted_by_enter(self):
        # A proposal age the generative layer clamped to the range floor (a
        # raw -5 becomes 0) passes the deterministic range check when Enter
        # accepts it (the generative clamp + the deterministic preflight).
        self._propose(_proposal(age=0, apparent_age=0))
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("自訂者", "", ""),
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.age, 0)
        self.assertEqual(self.char1.apparent_age, 0)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_typed_out_of_range_age_over_the_default_still_hits_the_range_check(self):
        self._propose(_proposal(age=20, apparent_age=20))
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("自訂者", "-1", "20"),
        )
        self.assertIn("角色建立失敗", output)
        self.assertTrue(self.char1.creation_pending)
        self.assertIsNone(self.char1.age)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_absent_background_and_affinity_stay_neutral(self):
        # The base proposal carries neither field: None rides the request and
        # the custom validator normalises it (no background key, neutral
        # affinity) — the pre-prefill outcome, unchanged.
        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("自訂者", "20", "20"),
        )
        self.assertIn("已建立", output)
        self.assertNotIn("background", self.char1.db.persona)
        self.assertEqual(self.char1.db.affinity_elements, [])

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_summary_shows_prefilled_values_and_absent_markers(self):
        self._propose(_proposal(**self._FULL))
        output = self.call(
            CmdCharacterConcept(),
            "構想 一個貓人少女",
            inputs=_stack("cancel"),
        )
        self.assertIn("姓名：雪貓", output)
        self.assertIn("實際年齡：20", output)
        self.assertIn("外表年齡：19", output)
        self.assertIn("背景：邊境孤兒，被商隊收養", output)
        self.assertIn(f"元素親和：{_element_display(_SYNTH_ELEMENT)}", output)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_summary_marks_absent_fields_and_neutral_affinity(self):
        self._propose(_proposal())
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("cancel"),
        )
        self.assertIn("姓名：（未提案，將由你輸入）", output)
        self.assertIn("實際年齡：（未提案，將由你輸入）", output)
        self.assertIn("背景：（未提案，將留空）", output)
        self.assertIn("元素親和：（未提案）", output)
        self.assertNotIn("預設：", output)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_summary_renders_explicitly_neutral_affinity_as_none(self):
        # The normalized empty tuple is a distinct outcome from an absent
        # field: the proposal explicitly landed on neutral affinity.
        self._propose(_proposal(affinity_elements=()))
        output = self.call(
            CmdCharacterConcept(),
            "構想 流浪的精靈劍士",
            inputs=_stack("cancel"),
        )
        self.assertIn("元素親和：（無）", output)
        self.assertNotIn("元素親和：（未提案）", output)

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_real_handler_empty_line_re_prompts_then_completes(self):
        # Production sync rack: the real cmdhandler's progressive loop plus
        # evmenu get_input must deliver an actual empty line into the
        # generator, keep the mandatory prompt open, and resume normally.
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
                self.assertEqual(
                    sum(
                        1
                        for t in prompts
                        if "角色姓名（輸入 cancel 取消）：" in t
                    ),
                    1,
                )
                self.assertTrue(self.char1.ndb._getinput)
                self.char1.execute_cmd("", session=self.session)
                queue.drain()
                self.char1.execute_cmd("   ", session=self.session)
                queue.drain()
                prompts = _messages(message_mock)
                self.assertEqual(
                    sum(
                        1
                        for t in prompts
                        if "角色姓名（輸入 cancel 取消）：" in t
                    ),
                    3,
                )
                self.assertTrue(self.char1.ndb._getinput)
                self.char1.execute_cmd("雪貓", session=self.session)
                queue.drain()
                self.char1.execute_cmd("20", session=self.session)
                queue.drain()
                self.char1.execute_cmd("20", session=self.session)
                queue.drain()
        finally:
            self.char1.msg = original_msg
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.key, "雪貓")

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_live_async_rack_empty_line_accepts_the_prefilled_name(self):
        # Production async rack: the _ConceptPromptCmdSet feeder must deliver
        # a blank line (the CMD_NOINPUT path) so Enter accepts the prefilled
        # default instead of stalling or dooming the flow.
        from twisted.internet import defer

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 一個貓人少女"
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            generator = command.func()
            with self.assertRaises(StopIteration):
                next(generator)
            held.callback(_proposal(**self._FULL))
            prompts = _messages(message_mock)
            self.assertTrue(any("預設：雪貓，Enter 採納" in t for t in prompts))
            self.char1.execute_cmd("", session=self.session)
            prompts = _messages(message_mock)
            self.assertTrue(
                any("實際年齡（預設：20，Enter 採納" in t for t in prompts)
            )
            self.char1.execute_cmd("", session=self.session)
            self.char1.execute_cmd("", session=self.session)
        finally:
            self.char1.msg = original_msg
        self.assertFalse(self.char1.creation_pending)
        self.assertEqual(self.char1.key, "雪貓")
        self.assertEqual(self.char1.age, 20)
        self.assertEqual(self.char1.db.affinity_elements, [_SYNTH_ELEMENT])
        self.assertFalse(self.char1.cmdset.has("ConceptPrompt"))

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_competing_activation_mid_prompt_releases_the_async_rack(self):
        # A browser-surface activation completes the character while the
        # async prompt chain is open. The next reply releases the
        # continuation quietly and clears the prompt state: the ConceptPrompt
        # set must stop consuming the now-active player's commands.
        from twisted.internet import defer

        held = defer.Deferred()
        patch_obj = self._patch.start()
        patch_obj.return_value = held
        self.addCleanup(self._patch.stop)
        command = CmdCharacterConcept()
        command.caller = self.char1
        command.account = self.account
        command.session = self.session
        command.args = "構想 一個貓人少女"
        generator = command.func()
        with self.assertRaises(StopIteration):
            next(generator)
        held.callback(_proposal(display_name="雪貓"))
        self.assertTrue(self.char1.cmdset.has("ConceptPrompt"))
        output = self.call(CmdCharacter(), _PRESET_COMMAND)
        self.assertIn("已建立", output)
        activated_key = self.char1.key
        self.char1.execute_cmd("20", session=self.session)
        self.assertFalse(self.char1.cmdset.has("ConceptPrompt"))
        # ndb lookups never raise for missing keys, so existence is the
        # getattr-None idiom the command surface itself uses.
        self.assertIsNone(getattr(self.char1.ndb, "concept_prompt", None))
        # The stale continuation never reached activation: the activated
        # character keeps the preset's identity, not the concept's.
        self.assertEqual(self.char1.key, activated_key)
        self.assertTrue(self.char1.key != "雪貓")

    @covers_requirement("character-creation-ux::the-creation-surface-offers-a-concept-driven-custom-entry")
    def test_competing_activation_mid_prompt_releases_the_sync_rack(self):
        # Same race on the production sync rack: after an independent
        # activation, the next get_input reply self-cleans the rack and the
        # generator completes without attempting activation.
        self._propose(_proposal())
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with QueuedDeferLater() as queue:
                self.char1.execute_cmd(
                    "character concept 流浪的精靈劍士", session=self.session
                )
                queue.drain()
                self.assertTrue(self.char1.ndb._getinput)
                output = self.call(CmdCharacter(), _PRESET_COMMAND)
                self.assertIn("已建立", output)
                activated_key = self.char1.key
                self.char1.execute_cmd("20", session=self.session)
                queue.drain()
        finally:
            self.char1.msg = original_msg
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))
        self.assertEqual(self.char1.key, activated_key)

    def test_terminal_safe_neutralises_controls_and_escapes_markup(self):
        rendered = _terminal_safe("故事\x1b[2J|r偽造|n\n第二行")
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\n", rendered)
        self.assertIn("||r", rendered)
        # Every pipe in the rendered text is an escape pair: with the pairs
        # removed no markup lead character remains.
        self.assertNotIn("|", rendered.replace("||", ""))

    def test_summary_and_prompts_render_hostile_proposal_text_inertly(self):
        hostile = {
            "display_name": "雪\r\n|r貓",
            "background": "故事\x1b[2J|r系統訊息|n",
        }
        summary = _proposal_summary(_proposal(**hostile))
        self.assertNotIn("\x1b", summary)
        self.assertEqual(
            len([line for line in summary.splitlines() if line.startswith("背景：")]),
            1,
        )
        self.assertEqual(
            len([line for line in summary.splitlines() if line.startswith("姓名：")]),
            1,
        )
        prompt = _name_prompt("雪\x1b[31m|r貓")
        self.assertNotIn("\x1b", prompt)
        self.assertNotIn("\n", prompt)

    def test_age_prompts_name_their_proposal_defaults(self):
        self.assertIn(
            "實際年齡（預設：20，Enter 採納，0 至 10000",
            _age_prompt("實際年齡", 20),
        )
        self.assertIn(
            "外表年齡（預設：19，Enter 採納，0 至 10000",
            _age_prompt("外表年齡", 19),
        )
        self.assertNotIn(
            "預設", _age_prompt("外表年齡", None)
        )
