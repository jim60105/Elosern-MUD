"""The transient concept action (retool-concept-transient-fill D1)."""
from web.webclient.actions.creation_actions import (
    _creation_activate_adapter,
    _creation_concept_adapter,
    _creation_custom_adapter,
    _creation_preset_adapter,
    _creation_reset_adapter,
    validate_creation_activate_payload,
    validate_creation_concept_payload,
    validate_creation_custom_payload,
    validate_creation_preset_payload,
    validate_creation_reset_payload,
)
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from world.rules.creation_wizard import draft_fingerprint, read_draft, save_custom_draft
import unittest
from ._support import (
    CreationActionBase,
    PERSONA_BLOCK,
    _T_ELF_SUBRACE,
    _T_RACE,
    _T_SUBRACE,
    _concept_payload,
    _element_keys,
    _proposal,
    await_result,
    balanced_allocations,
    custom_payload,
)


class CreationConceptTests(CreationActionBase):
    """The transient concept action (retool-concept-transient-fill D1)."""

    def _propose(self, proposal):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            # A fresh fired Deferred per call: a settled Deferred must not be
            # reused across successive applies.
            side_effect=lambda **kwargs: defer.succeed(proposal),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    def _degrade(self):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            side_effect=lambda **kwargs: defer.succeed(None),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    def _slot(self):
        from web.webclient.actions.creation_actions import PROPOSAL_NDB_KEY

        return getattr(self.fake_session.ndb, PROPOSAL_NDB_KEY, None)

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_concept_apply_fills_only_the_session_slot(self):
        self._propose(_proposal())
        result = await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "concept_applied")
        self.assertEqual(result["affected_panels"], ("creation",))
        # Zero persistent writes: no draft, no canonical surface, no persona.
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.traits.all(), [])
        self.assertFalse(self.character.attributes.has("persona"))
        slot = self._slot()
        self.assertIsNotNone(slot, "the proposal must be stored in the session slot")
        self.assertEqual(slot["revision"], 1)
        self.assertEqual(slot["owner_actor_id"], self.character.pk)
        self.assertEqual(slot["race"], _T_RACE)
        self.assertEqual(slot["subrace"], _T_SUBRACE)
        self.assertEqual(slot["allocations"], balanced_allocations(_T_RACE))
        self.assertEqual(slot["persona"], PERSONA_BLOCK)

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_slot_never_follows_a_puppet_switch(self):
        from twisted.internet import defer

        # An in-flight completion whose session stopped puppeting the admitted
        # actor writes nothing.
        held = defer.Deferred()
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        deferred = _creation_concept_adapter(
            self.character, _concept_payload(), self.fake_session
        )
        self.fake_session.puppet = None  # the session went OOC mid-flight
        held.callback(_proposal())
        result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(self._slot())

    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_slot_carries_carried_transient_fill_and_omits_absent(self):
        # The v3 slot mirrors the proposal: carried values ship (affinity as a
        # plain list, the normalized empty elf set included); absent values
        # write no key at all — never null (bump-creation-panel-proposal-v3).
        first = _element_keys(1)[0]
        self._propose(
            _proposal(
                display_name="咪咪",
                age=20,
                apparent_age=18,
                background="貓婆婆收養的孤女",
                affinity_elements=(first,),
            )
        )
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        self.assertEqual(slot["display_name"], "咪咪")
        self.assertEqual(slot["age"], 20)
        self.assertEqual(slot["apparent_age"], 18)
        self.assertEqual(slot["background"], "貓婆婆收養的孤女")
        self.assertEqual(slot["affinity_elements"], [first])

        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, slot)

        # A carried EMPTY affinity set (the normalized elf value) is a value:
        # it ships as the empty list, it is not omitted.
        self._propose(
            _proposal(
                race_key="elf",
                subrace_key=_T_ELF_SUBRACE.key,
                allocations=balanced_allocations("elf", _T_ELF_SUBRACE.key),
                affinity_elements=(),
            )
        )
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["affinity_elements"], [])

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_custom_save_and_reset_clear_the_slot(self):
        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertIsNotNone(self._slot())
        # A successful custom save consumes the pending fill.
        result = _creation_custom_adapter(
            self.character, custom_payload(), self.fake_session
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())
        # A later apply is cleared by a successful reset.
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertIsNotNone(self._slot())
        result = _creation_reset_adapter(self.character, {}, self.fake_session)
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_revision_keeps_rising_across_consumed_slots(self):
        # A consumed slot (save/reset cleared it) must never restart the
        # sequence: a mounted overlay's lastAppliedRevision would otherwise
        # ignore the next fresh apply at the colliding revision.
        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["revision"], 1)
        result = _creation_custom_adapter(
            self.character, custom_payload(), self.fake_session
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        self.assertIsNotNone(slot)
        self.assertEqual(
            slot["revision"], 2, "the revision counter survives a consumed slot"
        )
        # A reset consumes again; the next apply still rises.
        _creation_reset_adapter(self.character, {}, self.fake_session)
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["revision"], 3)

    @covers_requirement("creation-persona-persistence::the-creation-panel-offers-a-concept-field-and-adapter-sharing-the-guarded-pipeline")
    def test_offline_concept_degrades_without_state_change(self):
        self._degrade()
        result = await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        self.assertEqual(result["message"], "生成不可用，請手動創角")
        self.assertIsNone(read_draft(self.character))
        self.assertIsNone(self._slot())
        self.assertTrue(self.character.creation_pending)
        # The deterministic adapters remain fully usable afterwards.
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")

    def test_concept_payload_is_exact(self):
        self.assertEqual(
            validate_creation_concept_payload(_concept_payload()),
            _concept_payload(),
        )
        for bad in (
            {"concept": ""},
            {"concept": "  "},
            {"concept": "構" * 501},
            {},
            {"concept": "構想", "actor": 1},
            {"concept": "構想", "account": 1},
            {"concept": "構想", "session": 1},
            {"concept": "構想", "persona": {"personality": "x"}},
            {"concept": "構想", "skill": "flight"},
            {"concept": 5},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_concept_payload(bad)

    def test_unknown_fields_are_rejected_before_the_generative_layer(self):
        envelope = self._envelope(
            "creation.concept", {**_concept_payload(), "persona": {"personality": "x"}},
            request_id="concept-tampered-1",
        )
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal"
        )
        mock = patch_obj.start()
        self.addCleanup(patch_obj.stop)
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        mock.assert_not_called()
        self.assertIsNone(read_draft(self.character))

    def test_abnormal_puppet_cannot_reach_a_write_path(self):
        self.character.db_account = None
        result = await_result(
            _creation_concept_adapter(self.character, _concept_payload())
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_adapter_never_writes_canonical_state_directly(self):
        self._propose(_proposal())
        await_result(_creation_concept_adapter(self.character, _concept_payload()))
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.race, None)
        self.assertFalse(self.character.attributes.has("persona"))
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

if __name__ == "__main__":
    unittest.main()
