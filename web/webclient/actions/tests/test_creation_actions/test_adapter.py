"""Preset/custom/reset adapter integration against real Evennia state."""
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)
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
    _T_OTHER_SUBRACE,
    _T_PRESET,
    _T_RACE,
    _concept_payload,
    _element_keys,
    _proposal,
    await_result,
    balanced_allocations,
    custom_payload,
    custom_request,
)


class CreationAdapterTests(CreationActionBase):
    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_preset_selection_success(self):
        result = _creation_preset_adapter(self.character, {"preset_key": _T_PRESET})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "preset_saved")
        self.assertEqual(result["affected_panels"], ("creation",))
        draft = read_draft(self.character)
        self.assertEqual(draft["mode"], "preset")
        self.assertEqual(draft["preset_key"], _T_PRESET)
        self.assertTrue(self.character.creation_pending)

    def test_preset_unknown_key_rejected_without_mutation(self):
        result = _creation_preset_adapter(self.character, {"preset_key": "nope"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_preset")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_custom_save_success_uses_trimmed_name(self):
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "custom_saved")
        draft = read_draft(self.character)
        self.assertEqual(draft["mode"], "custom")
        self.assertEqual(draft["display_name"], "新角色")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_custom_over_bound_affinity_rejected_without_mutation(self):
        before = self.character.attributes.get("creation_draft")
        result = _creation_custom_adapter(
            self.character,
            custom_payload(affinity_elements=list(_element_keys(3))),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "over_bound_affinity")
        self.assertEqual(self.character.attributes.get("creation_draft"), before)
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("webclient-character-creation-ui::the-age-range-gate-is-server-authoritative-for-both-age-fields")
    def test_age_fields_rejected_out_of_range_independently(self):
        # Direct adapter calls bypass the wire validator, so out-of-range
        # values reach the deterministic age validator in preflight and the
        # stable codes come from the creation service.
        for label, overrides in (
            ("age", {"age": -1}),
            ("apparent_age", {"apparent_age": -1}),
        ):
            with self.subTest(label=label):
                result = _creation_custom_adapter(self.character, custom_payload(**overrides))
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], f"{label}_out_of_range")
                self.assertIsNone(read_draft(self.character))
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])

    def test_custom_domain_rejections_leave_canonical_surface_unchanged(self):
        before = {
            key: self.character.attributes.get(key)
            for key in ("age", "apparent_age", "race", "subrace", "creation_pending")
        }
        before_traits = self.character.traits.all()
        cases = {
            "bad name": dict(display_name="|rbad|n"),
            "markup name": dict(display_name="x{abc}"),
            "unknown race": dict(race="t_not_a_race"),
            "incompatible subrace": dict(
                race=_T_RACE, subrace=_T_OTHER_SUBRACE.key
            ),
            "off budget": dict(
                allocations={axis: 0 for axis in ALLOCATABLE_AXES}
            ),
            "off span": dict(
                allocations={**balanced_allocations(_T_RACE), "hp": 10_000}
            ),
        }
        for label, overrides in cases.items():
            with self.subTest(label=label):
                result = _creation_custom_adapter(self.character, custom_payload(**overrides))
                self.assertEqual(result["outcome"], "rejected", label)
                self.assertIsNone(read_draft(self.character))
                for key, value in before.items():
                    self.assertEqual(self.character.attributes.get(key), value)
                self.assertEqual(self.character.traits.all(), before_traits)

    def test_already_complete_rejected(self):
        # A saved draft plus activation through a non-wizard path leaves the
        # draft behind; a later creation action must reject as already complete.
        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(
            self.account, self.character, custom_request(),
        )
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")

    def test_activate_without_draft_rejected(self):
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_draft")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    def test_missing_or_unowned_account_rejected_before_any_write(self):
        self.character.db_account = None
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(read_draft(self.character))
        self.character.db_account = self.account
        class NotAPlayer:
            account = self.account
        result = _creation_custom_adapter(NotAPlayer(), custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")

    def test_reset_is_idempotent_and_keeps_pending(self):
        _creation_custom_adapter(self.character, custom_payload())
        self.assertIsNotNone(read_draft(self.character))
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "draft_cleared")
        self.assertIsNone(read_draft(self.character))
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_reset_rejects_an_activated_character_without_mutation(self):
        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(
            self.account, self.character, custom_request(),
        )
        self.assertFalse(self.character.creation_pending)
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertIsNone(read_draft(self.character))

    def test_pending_flip_while_in_flight_rejects_at_completion(self):
        from twisted.internet import defer

        from world.rules.character_creation import (
            activate_player_character,
        )

        held = defer.Deferred()
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        deferred = _creation_concept_adapter(self.character, _concept_payload())
        # The character is activated (via another entry) while in flight.
        activate_player_character(
            self.account, self.character,
            custom_request(),
        )
        held.callback(_proposal())
        result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertIsNone(read_draft(self.character))
        self.assertFalse(self.character.creation_pending)

    def test_adapter_never_writes_canonical_state_directly(self):
        _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.race, None)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

if __name__ == "__main__":
    unittest.main()
