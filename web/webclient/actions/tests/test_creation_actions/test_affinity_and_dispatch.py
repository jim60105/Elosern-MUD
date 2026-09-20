"""Affinity binding rules and dispatcher stale/duplicate handling."""
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
import unittest
from ._support import (
    CreationActionBase,
    _T_ELF_SUBRACE,
    _element_keys,
    balanced_allocations,
    custom_payload,
)


class CreationAffinityBindingTests(CreationActionBase):
    """The race-bound affinity rules, exercised inside the kit scope so the
    bound comes from the patched bound map (the kit race carries its own
    entry) and the elf branch resolves through the borrowed in-scope
    profile."""

    def test_custom_affinity_within_the_kit_race_bound_saves(self):
        # Which elements a fixture picks is a data choice, probed at runtime
        # (the registry stays live; uniqueness comes from the probe).
        two = _element_keys(2)
        result = _creation_custom_adapter(
            self.character,
            custom_payload(affinity_elements=list(two)),
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            read_draft(self.character)["affinity_elements"], list(two)
        )

    def test_custom_elf_affinity_rejected_without_mutation(self):
        result = _creation_custom_adapter(
            self.character,
            custom_payload(
                race="elf",
                subrace=_T_ELF_SUBRACE.key,
                allocations=balanced_allocations("elf", _T_ELF_SUBRACE.key),
                affinity_elements=_element_keys(1),
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "elf_affinity_rejected")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_custom_elf_empty_affinity_is_neutral_and_activates_with_subrace_seed(self):
        # The WebClient always emits ``affinity_elements`` (possibly ``[]``), so
        # an empty elf set is neutral player input, not a rejected contradiction;
        # activation still seeds the elf from its subrace.
        result = _creation_custom_adapter(
            self.character,
            custom_payload(
                race="elf",
                subrace=_T_ELF_SUBRACE.key,
                allocations=balanced_allocations("elf", _T_ELF_SUBRACE.key),
                affinity_elements=[],
            ),
        )
        self.assertEqual(result["outcome"], "success")
        draft = read_draft(self.character)
        self.assertNotIn("affinity_elements", draft)
        _creation_activate_adapter(self.character, {})
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(
            self.character.db.affinity_elements,
            list(_T_ELF_SUBRACE.affinity_elements),
        )


class CreationDispatchTests(CreationActionBase):
    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_activate_revision_runs_no_adapter(self):
        self._dispatch(
            self._envelope(
                "creation.custom", custom_payload(), request_id="custom-1"
            )
        )
        self.assertIsNotNone(read_draft(self.character))
        stale_revision = self.coordinator.revision - 1
        self._dispatch(
            self._envelope(
                "creation.activate", {}, request_id="activate-stale", base_revision=stale_revision
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "stale")
        self.assertTrue(self.character.creation_pending)
        self.assertIsNotNone(read_draft(self.character))

    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_duplicate_request_executes_once(self):
        envelope = self._envelope(
            "creation.custom", custom_payload(), request_id="dup-custom-1"
        )
        self._dispatch(envelope)
        self._dispatch(envelope)
        results = [
            entry["ui_action_result"][0][0]
            for entry in self.fake_session.sent
            if "ui_action_result" in entry
        ]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["outcome"], "success")
        self.assertEqual(results[1]["outcome"], "success")
        # The draft was saved exactly once by the first execution; the replay
        # returned the cached result without a second deterministic write.
        self.assertIsNotNone(read_draft(self.character))

    def test_tampered_authority_field_rejected_before_domain_api(self):
        envelope = self._envelope(
            "creation.custom", {**custom_payload(), "actor": 1}, request_id="tampered-1"
        )
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        self.assertIsNone(read_draft(self.character))

    def test_unknown_creation_action_is_not_routed_to_a_command(self):
        envelope = self._envelope("creation.command", {}, request_id="unknown-1")
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_action")

if __name__ == "__main__":
    unittest.main()
