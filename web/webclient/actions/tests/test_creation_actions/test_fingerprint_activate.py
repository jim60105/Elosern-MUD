"""Draft fingerprint binding and the atomic activation transaction."""
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
from world.rules.creation_wizard import draft_fingerprint, read_draft, save_custom_draft
from unittest.mock import patch
import unittest
from ._support import (
    CreationActionBase,
    _T_PRESET,
    _concept_payload,
    await_result,
    custom_payload,
    custom_request,
)


class CreationFingerprintBindingTests(CreationActionBase):
    """Server-side draft-fingerprint binding (fix-creation-finalization-safety D2)."""

    def test_custom_save_returns_and_records_the_stored_fingerprint(self):
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")
        fingerprint = draft_fingerprint(self.character)
        self.assertEqual(result["fingerprint"], fingerprint)
        self.assertEqual(
            getattr(self.character.ndb, "elosern_confirmed_draft_fingerprint", None),
            fingerprint,
        )

    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    @covers_requirement("creation-activation-gating::activation-is-bound-to-the-last-successfully-saved-draft")
    def test_stale_confirmation_is_refused_without_activating(self):
        _creation_custom_adapter(self.character, custom_payload())
        # Another entry replaces the stored draft without going through the
        # adapter, so the recorded confirmation now names an older draft.
        save_custom_draft(
            self.account,
            self.character,
            custom_request(
                display_name="較新草稿", age=21, apparent_age=21
            ),
        )
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "confirmation_stale")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(self.character.key, "pending-shell")

    def test_activate_after_a_draft_saved_outside_the_adapter_is_refused(self):
        # A draft stored by the deterministic save API directly (e.g. the
        # Telnet path) never passed through a confirmed adapter save; activation
        # must refuse rather than activate an unconfirmed draft.
        save_custom_draft(
            self.account,
            self.character,
            custom_request(),
        )
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    def test_activate_without_any_draft_still_rejects_with_no_draft(self):
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_draft")
        self.assertTrue(self.character.creation_pending)

    def test_preset_save_also_binds_the_confirmation_fingerprint(self):
        result = _creation_preset_adapter(self.character, {"preset_key": _T_PRESET})
        self.assertEqual(result["outcome"], "success")
        fingerprint = draft_fingerprint(self.character)
        self.assertEqual(result["fingerprint"], fingerprint)
        self.assertEqual(
            getattr(self.character.ndb, "elosern_confirmed_draft_fingerprint", None),
            fingerprint,
        )

    @covers_requirement("creation-activation-gating::activation-is-bound-to-the-last-successfully-saved-draft")
    @covers_requirement("webclient-character-creation-ui::web-activation-confirms-the-exact-draft-shown")
    def test_activate_after_a_rejected_save_is_refused_without_activating(self):
        # A rejected save invalidates the confirmation: the draft the player
        # was trying to save was not stored, so a leftover confirmation must
        # not be able to activate the older draft (webclient-character-
        # creation-ui "Save rejection followed by activation is refused").
        _creation_custom_adapter(self.character, custom_payload())
        rejected = _creation_custom_adapter(
            self.character, custom_payload(age=-1)
        )
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(rejected["code"], "age_out_of_range")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(self.character.key, "pending-shell")

    def test_rejected_preset_save_also_invalidates_the_confirmation(self):
        _creation_preset_adapter(self.character, {"preset_key": _T_PRESET})
        rejected = _creation_preset_adapter(
            self.character, {"preset_key": "nonexistent_preset"}
        )
        self.assertEqual(rejected["outcome"], "rejected")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_concept_outcomes_never_touch_the_confirmation_state(self):
        # The concept path saves no draft, so it neither preserves nor
        # manufactures an activation authorization: a degraded concept leaves
        # a still-valid confirmation intact (retool-concept-transient-fill
        # D1/D7), and activation of the confirmed draft still succeeds.
        from twisted.internet import defer

        _creation_custom_adapter(self.character, custom_payload())
        with patch(
            "server.ai_director_service.request_character_proposal",
            return_value=defer.succeed(None),
        ):
            deferred = _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        activate = _creation_activate_adapter(self.character, {})
        self.assertEqual(activate["outcome"], "success")
        self.assertEqual(activate["code"], "activated")


class CreationActivateIntegrationTests(CreationActionBase):
    def setUp(self):
        super().setUp()
        _creation_custom_adapter(self.character, custom_payload())

    @covers_requirement("webclient-character-creation-ui::activation-is-all-or-nothing-and-hands-off-to-exploration")
    def test_activation_clears_draft_and_hands_off_to_exploration(self):
        before_location = self.character.location
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "activated")
        self.assertEqual(result["affected_panels"], ())
        self.assertFalse(self.character.creation_pending)
        self.assertIsNone(read_draft(self.character))
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual(self.character.age, 20)
        # Activation performs no relocation: the shell stays in place.
        self.assertIs(self.character.location, before_location)
        self.assertIsNotNone(self.character.traits.magic_power)

    def test_draft_clear_failure_rolls_back_the_whole_activation(self):
        def fail(stage):
            if stage == "creation_draft":
                raise RuntimeError("injected clear failure")

        draft_before = dict(read_draft(self.character))
        from world.rules.creation_wizard import activate_draft

        with self.assertRaisesRegex(RuntimeError, "injected clear failure"):
            activate_draft(
                self.account, self.character,
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(read_draft(self.character), draft_before)
        self.assertEqual(self.character.key, "pending-shell")
        self.assertEqual(self.character.traits.all(), [])

    def test_concurrent_activations_apply_exactly_once(self):
        from world.rules.creation_wizard import activate_draft

        first = activate_draft(self.account, self.character)
        self.assertFalse(self.character.creation_pending)
        from world.rules.character_creation import CharacterCreationError

        with self.assertRaises(CharacterCreationError):
            activate_draft(self.account, self.character)
        self.assertEqual(self.character.key, first.display_name)
        self.assertEqual(read_draft(self.character), None)

if __name__ == "__main__":
    unittest.main()
